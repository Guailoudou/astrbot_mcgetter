from PIL import Image, ImageDraw, ImageFont
import asyncio
import io
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

import asyncio
import base64
import io
from typing import Optional, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage

def parse_motd_colors(motd_html: str) -> List[Tuple[str, Tuple[int, int, int]]]:
    """
    示例解析器，假设返回 [(文本, (R,G,B)), ...]
    实际应解析 HTML 格式（如 §a 文本等），这里简化
    """
    # 示例：返回带颜色的文本片段
    if not motd_html.strip():
        return [("无服务器描述", (150, 150, 150))]
    
    # 模拟解析结果
    colors = {
        'green': (85, 255, 85),
        'yellow': (255, 255, 0),
        'white': (255, 255, 255),
        'red': (255, 85, 85),
        'blue': (85, 85, 255),
    }
    segments = []
    for line in motd_html.split('\n'):
        if line.startswith('§'):
            color_code = line[1:2]  # §a → a
            color = colors.get(color_code, (255, 255, 255))
            text = line[2:]
            segments.append((text, color))
        else:
            segments.append((line, (255, 255, 255)))
    return segments


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
    """生成现代风格的服务器信息图片并返回base64编码"""

    # 异步获取图标
    server_icon = await fetch_icon(icon_base64)

    # 配置参数 - 更现代的配色方案
    BG_COLOR = (20, 20, 20)
    TEXT_COLOR = (220, 220, 220)
    ACCENT_COLOR = (85, 255, 85)  # 主色绿
    WARNING_COLOR = (255, 170, 0)
    ERROR_COLOR = (255, 85, 85)
    SECTION_BG = (30, 30, 30)  # 卡片背景
    CARD_BORDER = (40, 40, 40)  # 卡片边框
    SHADOW_COLOR = (0, 0, 0, 30)  # 半透明阴影
    RADIUS = 12  # 圆角半径

    # 字体配置
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

    # 解析MOTD
    motd_segments = parse_motd_colors(motd_html)

    # 计算布局
    icon_size = 64 if server_icon else 0
    padding_x = 20
    padding_y = 15
    spacing = 20
    line_height = 30

    # 计算高度
    player_lines = (len(players_list) // 4) + 1
    motd_lines = max(1, len([seg for seg in motd_segments if seg[0]]))
    header_height = 100
    motd_height = max(40, motd_lines * line_height)
    players_height = player_lines * line_height
    total_height = (
        header_height + 
        motd_height + 
        players_height + 
        4 * spacing
    )

    # 创建画布
    width = 600
    img = Image.new("RGBA", (width, total_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 添加轻微阴影（模拟浮起效果）
    shadow_img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)
    shadow_draw.rounded_rectangle(
        [padding_x+1, padding_y+1, width-padding_x-1, total_height-padding_y-1],
        radius=RADIUS,
        fill=SHADOW_COLOR
    )
    img.paste(shadow_img, (0, 0), shadow_img)

    # 绘制主内容区域
    x_start = padding_x + icon_size + 10
    y_start = padding_y

    # 服务器图标
    if server_icon:
        mask = Image.new("L", (64, 64), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 64, 64), fill=255)  # 圆形蒙版
        server_icon.thumbnail((64, 64))
        img.paste(server_icon, (padding_x, y_start), mask)

    # 服务器名称
    draw.text((x_start, y_start), server_name, font=title_font, fill=ACCENT_COLOR)
    y_start += 35

    # 版本 & 延迟
    version_text = f"版本: {server_version}"
    latency_color = ACCENT_COLOR if latency < 100 else WARNING_COLOR if latency < 200 else ERROR_COLOR
    latency_text = f"延迟: {latency}ms"

    draw.text((x_start, y_start), version_text, font=text_font, fill=TEXT_COLOR)
    draw.text((width - 150, y_start), latency_text, font=text_font, fill=latency_color)
    y_start += 30

    # 在线玩家数
    online_text = f"在线玩家 ({plays_online}/{plays_max})"
    draw.text((x_start, y_start), online_text, font=text_font, fill=ACCENT_COLOR)
    y_start += 40

    # MOTD 区域（卡片式）
    motd_y = y_start
    draw.rounded_rectangle(
        [padding_x, motd_y, width - padding_x, motd_y + motd_height],
        radius=RADIUS,
        fill=SECTION_BG,
        outline=CARD_BORDER,
        width=1
    )

    # 绘制 MOTD 文本（支持多行 + 颜色）
    current_y = motd_y + 10
    current_x = x_start + 10
    for text, color in motd_segments:
        if text:
            draw.text((current_x, current_y), text, font=motd_font, fill=color)
            # 粗略估算宽度
            w = len(text) * 14
            current_x += w
            if current_x > width - 200:
                current_x = x_start + 10
                current_y += line_height
        else:
            current_y += line_height
            current_x = x_start + 10
    y_start = motd_y + motd_height + 20

    # 玩家列表区域
    draw.text((x_start, y_start), "玩家列表", font=subtitle_font, fill=ACCENT_COLOR)
    y_start += 25

    # 玩家列表卡片
    players_y = y_start
    draw.rounded_rectangle(
        [padding_x, players_y, width - padding_x, players_y + players_height + 10],
        radius=RADIUS,
        fill=SECTION_BG,
        outline=CARD_BORDER,
        width=1
    )

    # 绘制玩家名字
    current_y = players_y + 10
    for i, chunk in enumerate([players_list[j:j+4] for j in range(0, len(players_list), 4)]):
        players_line = " • ".join(chunk)
        draw.text((x_start + 10, current_y), players_line, font=small_font, fill=TEXT_COLOR)
        current_y += line_height

    # 整体边框（外层）
    draw.rounded_rectangle(
        [padding_x, padding_y, width - padding_x, total_height - padding_y],
        radius=RADIUS,
        outline=ACCENT_COLOR,
        width=2
    )

    # 转为 base64
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return img_base64
