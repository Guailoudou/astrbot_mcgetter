from PIL import Image, ImageDraw, ImageFont
import asyncio
import io,re
from pathlib import Path
import base64
from typing import Optional, List, Tuple
async def load_font(font_size):
    # 尝试多路径加载
    font_paths = [
        Path(__file__).resolve().parent.parent/'resource'/'msyh.ttf',
        'msyh.ttf',  # 当前目录
        '/usr/share/fonts/zh_CN/msyh.ttf',  # Linux常见路径
        'C:/Windows/Fonts/msyh.ttc',  # Windows路径
        '/System/Library/Fonts/Supplemental/Songti.ttc'  # macOS路径
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(str(path), font_size)
        except OSError:
            continue
    
    # 全部失败时使用默认字体（添加中文支持）
    try:
        # 尝试加载PIL的默认中文字体
        return ImageFont.load_default().font_variant(size=font_size)
    except:
        return ImageFont.load_default()

async def fetch_icon(icon_base64: Optional[str] = None) -> Optional[Image.Image]:
    """处理Base64编码的服务器图标"""
    if not icon_base64:
        return None
    
    try:
        # 去除可能的Base64前缀
        if "," in icon_base64:
            icon_base64 = icon_base64.split(",", 1)[1]
        icon_data = base64.b64decode(icon_base64)
        return Image.open(io.BytesIO(icon_data)).convert("RGBA")
    except Exception as e:
        print(f"Base64图标解码失败: {str(e)}")
        return None

def parse_motd_colors(motd: str) -> List[Tuple[str, Tuple[int, int, int]]]:
    """解析 MOTD 颜色代码，返回 (文本, RGB) 列表"""
    if not motd.strip():
        return [("无服务器描述", (150, 150, 150))]

    color_map = {
        '0': (0, 0, 0), '1': (0, 0, 170), '2': (0, 170, 0), '3': (0, 170, 170),
        '4': (170, 0, 0), '5': (170, 0, 170), '6': (255, 170, 0), '7': (170, 170, 170),
        '8': (85, 85, 85), '9': (85, 85, 255), 'a': (85, 255, 85), 'b': (85, 255, 255),
        'c': (255, 85, 85), 'd': (255, 85, 255), 'e': (255, 255, 85), 'f': (255, 255, 255),
        'r': (255, 255, 255)  # 重置为白色
    }

    # 正确的正则表达式，匹配颜色代码
    pattern = r'§([0-9a-fr])'
    
    # 分割行
    lines = motd.split('\n')
    result = []

    for line in lines:
        if not line.strip():
            result.append(("", (255, 255, 255)))
            continue

        # 使用正则表达式分割，保留分隔符
        parts = re.split(pattern, line)
        
        current_color = (255, 255, 255)  # 默认白色
        
        i = 0
        while i < len(parts):
            part = parts[i]
            # 检查下一个元素是否是颜色代码
            if i + 1 < len(parts) and parts[i+1] in color_map:
                # 当前部分是文本，下一部分是颜色代码
                if part:
                    result.append((part, current_color))
                
                # 更新颜色
                current_color = color_map[parts[i+1]]
                i += 2  # 跳过颜色代码
            else:
                # 当前部分是文本
                if part:
                    result.append((part, current_color))
                i += 1
    
    return result

def render_motd_mc_style(parsed_motd: List[Tuple[str, Tuple[int, int, int]]], 
                        max_width: int, font_measure_func, 
                        max_lines: int = 2) -> List[List[Tuple[str, Tuple[int, int, int]]]]:
    """
    Minecraft风格的MOTD渲染，不同颜色在同一行显示，超过宽度才换行
    
    Args:
        parsed_motd: 解析后的MOTD文本段列表
        max_width: 最大行宽度（像素）
        font_measure_func: 字体测量函数，接受文本和字体，返回宽度
        max_lines: 最大显示行数，默认2行
        
    Returns:
        按行组织的文本段和颜色列表，每行是[(text, color), ...]
    """
    # 合并所有文本段，保留颜色信息
    all_segments = []
    for text, color in parsed_motd:
        if text:  # 跳过空文本
            all_segments.append((text, color))
    
    if not all_segments:
        return [[("无服务器描述", (150, 150, 150))]]
    
    lines = []
    current_line = []
    current_line_text = ""
    
    # 逐段添加到当前行，直到超过最大宽度
    for text, color in all_segments:
        # 尝试添加当前段
        test_text = current_line_text + text
        test_width = font_measure_func(test_text)
        
        if test_width <= max_width:
            # 可以添加到当前行
            current_line.append((text, color))
            current_line_text = test_text
        else:
            # 超过宽度，需要换行
            if current_line:  # 如果当前行不为空
                lines.append(current_line)
                if len(lines) >= max_lines:
                    break  # 达到最大行数，停止处理
            
            # 开始新行
            current_line = [(text, color)]
            current_line_text = text
    
    # 添加最后一行
    if current_line and len(lines) < max_lines:
        lines.append(current_line)
    
    # 如果没有内容，添加默认文本
    if not lines:
        lines.append([("无服务器描述", (150, 150, 150))])
    
    return lines


# ========================
# 主函数：生成服务器信息图（Minecraft风格MOTD）
# ========================

async def generate_server_info_image(
    players_list: list,
    latency: int,
    server_name: str,
    plays_max: int,
    plays_online: int,
    server_version: str,
    motd_html: str,
    icon_base64: Optional[str] = None
) -> str:
    # === 加载资源 ===
    server_icon = await fetch_icon(icon_base64)

    # === 配色 ===
    BG_COLOR = (20, 20, 20)
    TEXT_COLOR = (220, 220, 220)
    ACCENT_COLOR = (85, 255, 85)
    WARNING_COLOR = (255, 170, 0)
    ERROR_COLOR = (255, 85, 85)
    SECTION_BG = (30, 30, 30)
    CARD_BORDER = (50, 50, 50)
    RADIUS = 12

    # === 字体 ===
    try:
        title_font = await load_font(28)
        subtitle_font = await load_font(20)
        text_font = await load_font(18)
        small_font = await load_font(16)
        motd_font = await load_font(22)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        motd_font = ImageFont.load_default()

    # === 解析 MOTD ===
    motd_segments = parse_motd_colors(motd_html)

    # === 创建临时画布用于测量 ===
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    # === 布局参数 ===
    width = 600
    padding_x = 20
    icon_size = 64 if server_icon else 0
    text_x = padding_x + icon_size + 15
    line_height = 32
    motd_max_width = width - 2 * padding_x - 20  # 卡片内可用宽度

    # === Minecraft风格MOTD渲染 ===
    # 创建字体测量函数
    def measure_text_width(text):
        try:
            bbox = temp_draw.textbbox((0, 0), text, font=motd_font)
            return bbox[2] - bbox[0]
        except:
            # 如果字体有问题，使用简单长度估算
            return len(text) * 12  # 估算字符宽度

    # Minecraft风格渲染MOTD
    motd_lines = render_motd_mc_style(motd_segments, motd_max_width, measure_text_width, max_lines=2)

    # === 计算 MOTD 高度（最多2行）===
    motd_height = min(len(motd_lines), 2) * line_height + 20

    # === 玩家列表高度 ===
    player_chunks = [players_list[i:i+4] for i in range(0, len(players_list), 4)]
    players_height = len(player_chunks) * 35 + 20

    # === 总高度 ===
    total_height = (
        100 +               # 头部
        motd_height +       # 动态 MOTD 高度
        30 +                # "玩家列表" 标题
        players_height +    # 玩家列表
        70                 # 底部留白
    )

    # === 创建最终画布 ===
    img = Image.new("RGB", (width, total_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # === 图标 ===
    y_offset = 20
    if server_icon:
        mask = Image.new("L", (icon_size, icon_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, icon_size, icon_size), fill=255)
        server_icon = server_icon.resize((icon_size, icon_size), Image.LANCZOS)
        img.paste(server_icon, (padding_x, y_offset), mask)

    # === 服务器名称 ===
    draw.text((text_x, y_offset), server_name, font=title_font, fill=ACCENT_COLOR)
    y_offset += 35

    # === 版本 & 延迟 ===
    version_text = f"版本: {server_version}"
    latency_color = ACCENT_COLOR if latency < 100 else WARNING_COLOR if latency < 200 else ERROR_COLOR
    latency_text = f"延迟: {latency}ms"

    draw.text((text_x, y_offset), version_text, font=text_font, fill=TEXT_COLOR)
    draw.text((width - 150, y_offset), latency_text, font=text_font, fill=latency_color)
    y_offset += 30

    # === 在线玩家数 ===
    online_text = f"在线玩家 ({plays_online}/{plays_max})"
    draw.text((text_x, y_offset), online_text, font=text_font, fill=ACCENT_COLOR)
    y_offset += 40

    # === MOTD 卡片 ===
    motd_y = y_offset
    draw.rounded_rectangle(
        [padding_x, motd_y, width - padding_x, motd_y + motd_height],
        radius=RADIUS,
        fill=SECTION_BG,
        outline=CARD_BORDER,
        width=1
    )

    # === 绘制 MOTD（Minecraft风格）===
    current_y = motd_y + 10
    for line_segments in motd_lines[:2]:  # 最多显示2行
        current_x = padding_x + 10
        for text, color in line_segments:
            draw.text((current_x, current_y), text, font=motd_font, fill=color)
            # 测量文本宽度，更新x坐标
            try:
                bbox = draw.textbbox((current_x, current_y), text, font=motd_font)
                current_x = bbox[2]
            except:
                current_x += len(text) * 12  # 估算宽度
        current_y += line_height

    y_offset = motd_y + motd_height + 20

    # === 玩家列表标题 ===
    draw.text((text_x, y_offset), "玩家列表", font=subtitle_font, fill=ACCENT_COLOR)
    y_offset += 25

    # === 玩家列表卡片 ===
    players_start_y = y_offset
    draw.rounded_rectangle(
        [padding_x, players_start_y, width - padding_x, players_start_y + players_height],
        radius=RADIUS,
        fill=SECTION_BG,
        outline=CARD_BORDER,
        width=1
    )

    current_y = players_start_y + 10
    for chunk in player_chunks:
        players_line = " • ".join(chunk)
        draw.text((text_x + 10, current_y), players_line, font=small_font, fill=TEXT_COLOR)
        current_y += 28

    # === 外层边框 ===
    draw.rounded_rectangle(
        [10, 10, width - 10, total_height - 10],
        radius=RADIUS,
        outline=ACCENT_COLOR,
        width=2
    )

    # === 输出 base64 ===
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")