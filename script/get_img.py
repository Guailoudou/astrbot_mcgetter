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

import re
from html import unescape

def parse_motd_colors(motd_html: str):
    """
    解析带颜色的MOTD HTML文本
    返回解析后的文本段落和对应的颜色列表
    """
    if not motd_html:
        return [("无服务器描述", (255, 255, 255))]
    
    # 清理HTML实体
    motd_html = unescape(motd_html)
    
    # Minecraft颜色代码映射
    color_map = {
        '0': (0, 0, 0),       # 黑色
        '1': (0, 0, 170),     # 深蓝色
        '2': (0, 170, 0),     # 深绿色
        '3': (0, 170, 170),   # 深青色
        '4': (170, 0, 0),     # 深红色
        '5': (170, 0, 170),   # 紫色
        '6': (255, 170, 0),   # 金色
        '7': (170, 170, 170), # 灰色
        '8': (85, 85, 85),    # 深灰色
        '9': (85, 85, 255),   # 蓝色
        'a': (85, 255, 85),   # 绿色
        'b': (85, 255, 255),  # 青色
        'c': (255, 85, 85),   # 红色
        'd': (255, 85, 255),  # 粉色
        'e': (255, 255, 85),  # 黄色
        'f': (255, 255, 255), # 白色
    }
    
    # 默认颜色
    default_color = (255, 255, 255)
    current_color = default_color
    
    # 按行分割
    lines = motd_html.split('<br>')
    result = []
    
    for line in lines:
        if not line.strip():
            result.append(("", default_color))
            continue
            
        # 解析颜色代码
        segments = []
        last_end = 0
        
        # 查找所有颜色代码
        pattern = r'§([0-9a-f])'
        matches = list(re.finditer(pattern, line))
        
        if not matches:
            # 没有颜色代码，使用当前颜色
            clean_text = re.sub(r'<[^>]+>', '', line).strip()
            if clean_text:
                result.append((clean_text, current_color))
            continue
            
        # 处理带颜色的文本
        for i, match in enumerate(matches):
            start, end = match.span()
            color_code = match.group(1)
            
            # 获取颜色
            color = color_map.get(color_code, default_color)
            
            # 添加前面的文本（如果有的话）
            if start > last_end:
                text_segment = line[last_end:start]
                clean_text = re.sub(r'<[^>]+>', '', text_segment).strip()
                if clean_text:
                    segments.append((clean_text, current_color))
            
            # 更新当前颜色
            current_color = color
            last_end = end
        
        # 添加最后一段文本
        if last_end < len(line):
            text_segment = line[last_end:]
            clean_text = re.sub(r'<[^>]+>', '', text_segment).strip()
            if clean_text:
                segments.append((clean_text, current_color))
        
        # 合并相同颜色的相邻段落
        if segments:
            merged_segments = []
            for text, color in segments:
                if merged_segments and merged_segments[-1][1] == color:
                    merged_segments[-1] = (merged_segments[-1][0] + text, color)
                else:
                    merged_segments.append((text, color))
            
            # 将段落添加到结果中
            for segment in merged_segments:
                if segment[0]:
                    result.append(segment)
        
        # 如果一行没有有效文本，添加空行
        if not segments:
            result.append(("", default_color))
    
    # 如果没有解析出任何内容，添加默认文本
    if not result:
        result.append(("无服务器描述", default_color))
        
    return result

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
    """生成服务器信息图片并返回base64编码"""
    
    # 异步获取图标
    server_icon = await fetch_icon(icon_base64)
    
    # 配置参数
    BG_COLOR = (34, 34, 34)
    TEXT_COLOR = (255, 255, 255)
    ACCENT_COLOR = (85, 255, 85)
    WARNING_COLOR = (255, 170, 0)
    ERROR_COLOR = (255, 85, 85)
    SECTION_BG = (45, 45, 45)  # 区块背景色
    
    # 字体配置
    try:
        title_font = await load_font(30)
        text_font = await load_font(20)
        small_font = await load_font(18)
        motd_font = await load_font(22)
    except IOError:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        motd_font = ImageFont.load_default()
    
    # 解析MOTD颜色
    motd_segments = parse_motd_colors(motd_html)
    
    # 计算布局参数
    icon_size = 64 if server_icon else 0
    base_y = 20
    text_x = 20 + icon_size + 20
    
    # 自动计算图片高度（增加MOTD区域）
    line_height = 30
    player_lines = (len(players_list) // 4) + 1
    motd_lines = max(1, len([seg for seg in motd_segments if seg[0]]))  # 计算非空行数
    img_height = 220 + (player_lines * line_height) + (motd_lines * 30) + (20 if server_icon else 0)
    
    # 创建画布
    img = Image.new("RGB", (600, img_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 绘制服务器图标
    if server_icon:
        icon_mask = Image.new("L", (64, 64), 0)
        mask_draw = ImageDraw.Draw(icon_mask)
        mask_draw.rounded_rectangle((0, 0, 64, 64), radius=10, fill=255)
        server_icon.thumbnail((64, 64))
        img.paste(server_icon, (20, base_y), icon_mask)
    
    # 服务器基本信息区域 - 添加背景框
    draw.rounded_rectangle([15, 15, img.width-15, 150], radius=10, fill=SECTION_BG, width=2)
    
    # 服务器名称
    draw.text((text_x, base_y), server_name, font=title_font, fill=ACCENT_COLOR)
    base_y += 40
    
    # 版本和延迟信息
    version_text = f"版本: {server_version}"
    latency_color = ACCENT_COLOR if latency < 100 else WARNING_COLOR if latency < 200 else ERROR_COLOR
    latency_text = f"延迟: {latency}ms"
    
    draw.text((text_x, base_y), version_text, font=text_font, fill=TEXT_COLOR)
    draw.text((400, base_y), latency_text, font=text_font, fill=latency_color)
    base_y += 40
    
    # 在线玩家数
    online_text = f"在线玩家 ({plays_online}/{plays_max})"
    draw.text((text_x, base_y), online_text, font=text_font, fill=ACCENT_COLOR)
    base_y += 50  # 增加间距
    
    # MOTD信息区域 - 添加背景框
    motd_start_y = base_y
    if motd_segments:
        current_y = motd_start_y
        current_x = text_x
        
        # 绘制MOTD背景框
        motd_bg_height = max(40, motd_lines * 30)
        draw.rounded_rectangle([15, motd_start_y-10, img.width-15, motd_start_y+motd_bg_height], 
                              radius=8, fill=SECTION_BG, width=1)
        
        # 显示MOTD文本（支持颜色）
        for text, color in motd_segments:
            if text:
                draw.text((current_x, current_y), text, font=motd_font, fill=color)
                # 简单估算文本宽度，实际应用中可以使用更精确的方法
                text_width = len(text) * 12  # 粗略估算每个字符12像素
                current_x += text_width
            else:
                # 空行处理
                current_y += 30
                current_x = text_x
        
        base_y = motd_start_y + motd_bg_height + 20
    else:
        # 没有MOTD时也保留占位区域
        draw.rounded_rectangle([15, motd_start_y-10, img.width-15, motd_start_y+40], 
                              radius=8, fill=SECTION_BG, width=1)
        draw.text((text_x, motd_start_y), "无服务器描述", font=motd_font, fill=(150, 150, 150))
        base_y = motd_start_y + 60
    
    # 玩家列表区域标题
    draw.text((text_x-5, base_y), "玩家列表", font=text_font, fill=ACCENT_COLOR)
    base_y += 30
    
    # 玩家列表区域 - 添加背景框
    players_start_y = base_y
    if players_list:
        chunks = [players_list[i:i+4] for i in range(0, len(players_list), 4)]
        for chunk in chunks:
            players_line = " • ".join(chunk)
            draw.text((text_x + 20, base_y), players_line, font=small_font, fill=TEXT_COLOR)
            base_y += line_height
            
        # 为玩家列表添加背景框
        draw.rounded_rectangle([15, players_start_y-15, img.width-15, base_y+10], 
                              radius=8, outline=(70, 70, 70), width=1)
    else:
        draw.text((text_x + 20, base_y), "未获取到玩家数据", font=small_font, fill=TEXT_COLOR)
        base_y += line_height
        # 为玩家列表添加背景框
        draw.rounded_rectangle([15, players_start_y-15, img.width-15, base_y+10], 
                              radius=8, outline=(70, 70, 70), width=1)
    
    # 整体边框
    draw.rounded_rectangle([10, 10, img.width-10, img.height-10], radius=12, outline=ACCENT_COLOR, width=3)
    
    # 转换为base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # 返回base64 bytes
    return img_base64
