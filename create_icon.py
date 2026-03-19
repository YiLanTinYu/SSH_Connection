#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
生成应用程序图标 app.ico
运行此脚本后会在项目根目录生成 app.ico 文件
需要安装: pip install Pillow
"""

import os
import sys

def create_icon():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("正在使用 PyQt5 生成图标...")
        _create_icon_qt()
        return

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 背景渐变（用矩形近似）
        for y in range(size):
            ratio = y / size
            r = int(21  + (0   - 21)  * ratio)
            g = int(101 + (188 - 101) * ratio)
            b = int(192 + (212 - 192) * ratio)
            draw.rectangle([(0, y), (size, y + 1)], fill=(r, g, b, 255))

        # 圆角遮罩
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        radius = max(2, size // 8)
        mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
        img.putalpha(mask)

        # 绘制网络节点
        center = size // 2
        top_y  = size // 5
        bot_y  = size * 3 // 5
        left_x = size // 4
        right_x= size * 3 // 4
        r_node = max(2, size // 10)

        # 连线
        line_w = max(1, size // 20)
        draw.line([(center, top_y), (left_x, bot_y)],  fill=(255, 255, 255, 220), width=line_w)
        draw.line([(center, top_y), (right_x, bot_y)], fill=(255, 255, 255, 220), width=line_w)
        draw.line([(left_x, bot_y), (right_x, bot_y)], fill=(255, 255, 255, 220), width=line_w)

        # 节点圆
        for nx, ny in [(center, top_y), (left_x, bot_y), (right_x, bot_y)]:
            draw.ellipse([nx - r_node, ny - r_node, nx + r_node, ny + r_node],
                         fill=(255, 255, 255, 255))

        images.append(img)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
    images[0].save(
        out_path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"[OK] 图标已生成: {out_path}")


def _create_icon_qt():
    """使用 PyQt5 生成 ICO 文件"""
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QBrush, QPen, QIcon
        from PyQt5.QtCore import Qt, QRect
        import sys

        app = QApplication.instance() or QApplication(sys.argv)

        size = 256
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor("#1565C0"))
        grad.setColorAt(1.0, QColor("#00BCD4"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(8, 8, size - 16, size - 16, 40, 40)

        # 节点
        cx, ty = size // 2, size // 5
        lx, rx = size // 4, size * 3 // 4
        by     = size * 3 // 5
        r      = size // 12

        p.setPen(QPen(QColor(255, 255, 255, 210), size // 22))
        p.drawLine(cx, ty, lx, by)
        p.drawLine(cx, ty, rx, by)
        p.drawLine(lx, by, rx, by)

        p.setBrush(QBrush(QColor("white")))
        p.setPen(Qt.NoPen)
        for nx, ny in [(cx, ty), (lx, by), (rx, by)]:
            p.drawEllipse(nx - r, ny - r, r * 2, r * 2)

        p.end()

        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
        pix.save(out_path, "ICO")
        print(f"[OK] 图标已生成 (Qt): {out_path}")

    except Exception as e:
        print(f"[WARN] 图标生成失败: {e}")
        print("打包时将使用默认图标")


if __name__ == "__main__":
    create_icon()
