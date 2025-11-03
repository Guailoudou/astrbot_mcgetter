from PIL import Image, ImageDraw, ImageFont, ImageFilter
import asyncio
import io
import re
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

def create_gradient(width, height, start_color, end_color):
    """创建线性渐变背景"""
    gradient = Image.new('RGBA', (width, height), color=0)
    draw = ImageDraw.Draw(gradient)
    
    # 计算颜色渐变步长
    r_step = (end_color[0] - start_color[0]) / height
    g_step = (end_color[1] - start_color[1]) / height
    b_step = (end_color[2] - start_color[2]) / height
    
    # 绘制渐变
    for y in range(height):
        r = int(start_color[0] + r_step * y)
        g = int(start_color[1] + g_step * y)
        b = int(start_color[2] + b_step * y)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return gradient

def create_card_background(width, height, color, radius=12, glow_color=None, glow_radius=0):
    """创建卡片背景，支持圆角和发光效果"""
    card = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    
    # 绘制圆角矩形
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=color)
    
    # 添加发光效果
    if glow_color and glow_radius > 0:
        # 创建发光层
        glow = Image.new('RGBA', (width + glow_radius*2, height + glow_radius*2), color=(0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        
        # 绘制发光圆角矩形
        glow_draw.rounded_rectangle(
            [glow_radius, glow_radius, width + glow_radius, height + glow_radius], 
            radius=radius + glow_radius, 
            fill=glow_color
        )
        
        # 应用模糊效果
        glow = glow.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        
        # 将发光层粘贴到卡片下方
        card_with_glow = Image.new('RGBA', (width + glow_radius*2, height + glow_radius*2), color=(0, 0, 0, 0))
        card_with_glow.paste(glow, (0, 0))
        card_with_glow.paste(card, (glow_radius, glow_radius))
        
        return card_with_glow
    
    return card

def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0), shadow_offset=(2, 2)):
    """绘制带阴影的文本"""
    # 绘制阴影
    shadow_x, shadow_y = position[0] + shadow_offset[0], position[1] + shadow_offset[1]
    draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_color)
    
    # 绘制主文本
    draw.text(position, text, font=font, fill=fill)

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

    # === 现代化配色方案 ===
    # 主色调：深蓝到紫色渐变
    GRADIENT_START = (20, 25, 60)
    GRADIENT_END = (40, 20, 80)
    
    # 文本颜色
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (200, 200, 220)
    
    # 强调色
    ACCENT_PRIMARY = (85, 255, 150)  # 鲜亮绿色
    ACCENT_SECONDARY = (255, 170, 85)  # 橙色
    
    # 状态颜色
    STATUS_GOOD = (85, 255, 150)
    STATUS_WARNING = (255, 200, 85)
    STATUS_ERROR = (255, 85, 85)
    
    # 卡片颜色
    CARD_BG = (30, 35, 70, 220)  # 半透明深蓝
    CARD_BORDER = (60, 70, 120)
    CARD_GLOW = (80, 100, 200, 100)  # 发光效果
    
    # 圆角半径
    RADIUS = 16

    # === 字体 ===
    try:
        title_font = await load_font(32)
        subtitle_font = await load_font(22)
        text_font = await load_font(18)
        small_font = await load_font(16)
        motd_font = await load_font(24)
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
    width = 640
    padding_x = 24
    padding_y = 24
    icon_size = 80 if server_icon else 0
    text_x = padding_x + icon_size + 20
    line_height = 36
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
    motd_height = min(len(motd_lines), 2) * line_height + 30

    # === 玩家列表高度 ===
    player_chunks = [players_list[i:i+4] for i in range(0, len(players_list), 4)]
    players_height = len(player_chunks) * 35 + 30

    # === 总高度 ===
    total_height = (
        120 +               # 头部
        motd_height +       # 动态 MOTD 高度
        40 +                # "玩家列表" 标题
        players_height +    # 玩家列表
        40                  # 底部留白
    )

    # === 创建最终画布 ===
    # 创建渐变背景
    gradient_bg = create_gradient(width, total_height, GRADIENT_START, GRADIENT_END)
    img = gradient_bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # === 头部卡片 ===
    header_card = create_card_background(
        width - 2 * padding_x, 
        100, 
        CARD_BG, 
        radius=RADIUS, 
        glow_color=CARD_GLOW, 
        glow_radius=5
    )
    img.paste(header_card, (padding_x - 5, padding_y - 5), header_card)

    # === 图标 ===
    y_offset = padding_y
    if server_icon:
        # 创建圆形图标
        mask = Image.new("L", (icon_size, icon_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, icon_size, icon_size), fill=255)
        
        # 调整图标大小并应用圆形遮罩
        server_icon = server_icon.resize((icon_size, icon_size), Image.LANCZOS)
        icon_with_border = Image.new("RGBA", (icon_size + 4, icon_size + 4), CARD_BORDER)
        icon_with_border.paste(server_icon, (2, 2), mask)
        
        # 添加图标阴影
        shadow = Image.new("RGBA", (icon_size + 8, icon_size + 8), (0, 0, 0, 100))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((4, 4, icon_size + 4, icon_size + 4), fill=(0, 0, 0, 100))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
        
        img.paste(shadow, (padding_x - 2, padding_y - 2), shadow)
        img.paste(icon_with_border, (padding_x, padding_y), icon_with_border)

    # === 服务器名称 ===
    draw_text_with_shadow(
        draw, 
        (text_x, y_offset + 5), 
        server_name, 
        font=title_font, 
        fill=ACCENT_PRIMARY,
        shadow_color=(0, 0, 0, 180)
    )
    y_offset += 45

    # === 版本 & 延迟 ===
    version_text = f"版本: {server_version}"
    latency_color = STATUS_GOOD if latency < 100 else STATUS_WARNING if latency < 200 else STATUS_ERROR
    latency_text = f"延迟: {latency}ms"

    draw_text_with_shadow(
        draw, 
        (text_x, y_offset), 
        version_text, 
        font=text_font, 
        fill=TEXT_SECONDARY,
        shadow_color=(0, 0, 0, 150)
    )
    
    # 绘制延迟指示器
    latency_x = width - padding_x - 150
    draw_text_with_shadow(
        draw, 
        (latency_x, y_offset), 
        latency_text, 
        font=text_font, 
        fill=latency_color,
        shadow_color=(0, 0, 0, 150)
    )
    
    # 添加延迟条形图
    bar_width = 100
    bar_height = 8
    bar_x = latency_x + 80
    bar_y = y_offset + 8
    
    # 背景条
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
        radius=4,
        fill=(50, 50, 70)
    )
    
    # 填充条
    fill_width = min(bar_width, (bar_width * (1 - latency / 500))) if latency < 500 else 0
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
        radius=4,
        fill=latency_color
    )
    
    y_offset += 35

    # === 在线玩家数 ===
    online_text = f"在线玩家 ({plays_online}/{plays_max})"
    draw_text_with_shadow(
        draw, 
        (text_x, y_offset), 
        online_text, 
        font=text_font, 
        fill=ACCENT_SECONDARY,
        shadow_color=(0, 0, 0, 150)
    )
    
    # 添加玩家数量指示器
    player_bar_width = 150
    player_bar_height = 10
    player_bar_x = text_x + len(online_text) * 10 + 10
    player_bar_y = y_offset + 5
    
    # 背景条
    draw.rounded_rectangle(
        [player_bar_x, player_bar_y, player_bar_x + player_bar_width, player_bar_y + player_bar_height],
        radius=5,
        fill=(50, 50, 70)
    )
    
    # 填充条
    player_fill_width = (player_bar_width * plays_online) / plays_max if plays_max > 0 else 0
    draw.rounded_rectangle(
        [player_bar_x, player_bar_y, player_bar_x + player_fill_width, player_bar_y + player_bar_height],
        radius=5,
        fill=ACCENT_SECONDARY
    )
    
    y_offset += padding_y + 10

    # === MOTD 卡片 ===
    motd_y = y_offset
    motd_card = create_card_background(
        width - 2 * padding_x, 
        motd_height, 
        CARD_BG, 
        radius=RADIUS, 
        glow_color=CARD_GLOW, 
        glow_radius=3
    )
    img.paste(motd_card, (padding_x - 3, motd_y - 3), motd_card)

    # === 绘制 MOTD（Minecraft风格）===
    current_y = motd_y + 15
    for line_segments in motd_lines[:2]:  # 最多显示2行
        current_x = padding_x + 15
        for text, color in line_segments:
            # 为MOTD文本添加轻微阴影
            shadow_x, shadow_y = current_x + 1, current_y + 1
            draw.text((shadow_x, shadow_y), text, font=motd_font, fill=(0, 0, 0, 180))
            draw.text((current_x, current_y), text, font=motd_font, fill=color)
            
            # 测量文本宽度，更新x坐标
            try:
                bbox = draw.textbbox((current_x, current_y), text, font=motd_font)
                current_x = bbox[2]
            except:
                current_x += len(text) * 12  # 估算宽度
        current_y += line_height

    y_offset = motd_y + motd_height + 25

    # === 玩家列表标题 ===
    draw_text_with_shadow(
        draw, 
        (text_x, y_offset), 
        "玩家列表", 
        font=subtitle_font, 
        fill=ACCENT_PRIMARY,
        shadow_color=(0, 0, 0, 150)
    )
    y_offset += 30

    # === 玩家列表卡片 ===
    players_start_y = y_offset
    players_card = create_card_background(
        width - 2 * padding_x, 
        players_height, 
        CARD_BG, 
        radius=RADIUS, 
        glow_color=CARD_GLOW, 
        glow_radius=3
    )
    img.paste(players_card, (padding_x - 3, players_start_y - 3), players_card)

    current_y = players_start_y + 15
    for chunk in player_chunks:
        players_line = " • ".join(chunk)
        draw_text_with_shadow(
            draw, 
            (text_x + 10, current_y), 
            players_line, 
            font=small_font, 
            fill=TEXT_SECONDARY,
            shadow_color=(0, 0, 0, 120)
        )
        current_y += 28

    # === 装饰元素 ===
    # 添加顶部装饰光效
    overlay = Image.new('RGBA', (width, total_height), color=(0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # 左上角光效
    for i in range(10):
        alpha = 100 - i * 10
        overlay_draw.ellipse(
            [0 - i*20, 0 - i*20, 150 + i*10, 150 + i*10],
            fill=(100, 150, 255, alpha)
        )
    
    # 右上角光效
    for i in range(10):
        alpha = 80 - i * 8
        overlay_draw.ellipse(
            [width - 150 - i*10, 0 - i*20, width + i*20, 150 + i*10],
            fill=(150, 100, 255, alpha)
        )
    
    # 将光效叠加到主图像
    img = Image.alpha_composite(img, overlay)

    # === 输出 base64 ===
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")