"""Generate icon.ico for The Earful Tower."""
from PIL import Image, ImageDraw, ImageFont

EMOJI_FONT = r"C:\Windows\Fonts\seguiemj.ttf"
LABEL_FONT = r"C:\Windows\Fonts\segoeui.ttf"

BG      = (18, 24, 48, 255)      # deep navy
ACCENT  = (82, 182, 255, 255)    # sky blue


def draw_frame(size: int) -> Image.Image:
    f = size / 256
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # rounded background
    r = max(4, int(52 * f))
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    # 👂 emoji centered on upper 2/3
    font_size = max(8, int(148 * f))
    try:
        font = ImageFont.truetype(EMOJI_FONT, font_size)
        draw.text((size // 2, int(size * 0.45)), "👂",
                  font=font, anchor="mm", embedded_color=True)
    except Exception:
        pass

    # "ET" small text at bottom — only for larger sizes
    if size >= 48:
        try:
            lf = ImageFont.truetype(LABEL_FONT, max(8, int(36 * f)))
            draw.text((size // 2, int(size * 0.87)), "EARFUL TOWER",
                      font=lf, anchor="mm", fill=(180, 210, 255, 220))
        except Exception:
            pass

    return img


def main():
    sizes   = [256, 128, 64, 48, 32, 16]
    frames  = [draw_frame(s) for s in sizes]
    out     = "icon.ico"
    frames[0].save(
        out, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"saved {out}")


if __name__ == "__main__":
    main()
