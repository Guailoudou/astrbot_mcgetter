from PIL import Image, ImageDraw, ImageFont
import asyncio
import io,re
from pathlib import Path
import base64
from typing import Optional

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
            return ImageFont.truetype(path, font_size)
        except OSError:
            continue
    
    # 全部失败时使用默认字体（添加中文支持）
    try:
        # 尝试加载PIL的默认中文字体
        return ImageFont.load_default().font_variant(size=font_size)
    except:
        return ImageFont.load_default()

# 在代码中替换字体加载部分
title_font = load_font(30)
text_font = load_font(20)
small_font = load_font(18)

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



from typing import Optional, List, Tuple

from PIL import Image, ImageDraw, ImageFont,ImageColor
from PIL.Image import Image as PILImage
def parse_motd_colors(motd: str) -> List[Tuple[str, Tuple[int, int, int]]]:
    """解析 MOTD 颜色代码，返回 (文本, RGB) 列表"""
    if not motd.strip():
        return [("无服务器描述", (150, 150, 150))]

    color_map = {
        '0': (0, 0, 0), '1': (0, 0, 170), '2': (0, 170, 0), '3': (0, 170, 170),
        '4': (170, 0, 0), '5': (170, 0, 170), '6': (255, 170, 0), '7': (170, 170, 170),
        '8': (85, 85, 85), '9': (85, 85, 255), 'a': (85, 255, 85), 'b': (85, 255, 255),
        'c': (255, 85, 85), 'd': (255, 85, 255), 'e': (255, 255, 85), 'f': (255, 255, 255),
        'r': (255, 255, 255)
    }

    result = []
    current_color = color_map['f']
    
    # 使用split方式处理
    segments = re.split(r'(§[0-9a-fr]§?)', motd)
    
    for segment in segments:
        if not segment:
            continue
            
        if segment.startswith('§'):
            if len(segment) >= 2 and segment[1] in color_map:
                # 是颜色代码
                code = segment[1]
                if code == 'r':
                    current_color = color_map['f']
                else:
                    current_color = color_map[code]
            else:
                # 单独的§符号
                result.append(("§", current_color))
        else:
            # 普通文本
            result.append((segment, current_color))
            
    return result if result else [("无服务器描述", (150, 150, 150))]


# ========================
# 主函数：生成服务器信息图（最终版）
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

    # === 每个段单独换行（保留颜色）===
    wrapped_lines = []  # [(line_text, color), ...]
    current_line = ""
    current_color = None

    for text, color in motd_segments:
        if text == "":
            if current_line:
                wrapped_lines.append((current_line, current_color))
                current_line = ""
            wrapped_lines.append(("", None))  # 空行
            current_color = None
        else:
            # 添加到当前行
            new_line = current_line + text
            bbox = temp_draw.textbbox((0, 0), new_line, font=motd_font)
            width = bbox[2] - bbox[0]
            if width <= motd_max_width:
                current_line = new_line
                current_color = color
            else:
                # 换行
                if current_line:
                    wrapped_lines.append((current_line, current_color))
                current_line = text
                current_color = color

    # 提交最后一行
    if current_line:
        wrapped_lines.append((current_line, current_color))

    # === 计算 MOTD 高度 ===
    motd_height = len(wrapped_lines) * line_height + 20

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
    img = Image.new("RGB", (600, total_height), color=BG_COLOR)
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

    # === 绘制 MOTD ===
    current_y = motd_y + 10
    for line_text, color in wrapped_lines:
        if line_text == "":
            current_y += line_height
        else:
            draw.text((padding_x + 10, current_y), line_text, font=motd_font, fill=color)
            current_y += line_height

    y_offset = motd_y + motd_height + 20

    # === 玩家列表标题 ===
    draw.text((text_x, y_offset), "玩家列表", font=subtitle_font, fill=ACCENT_COLOR)
    y_offset += 35

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