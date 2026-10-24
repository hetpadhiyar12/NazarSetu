"""
Generate realistic sample images for quick 1-click hackathon demonstration.
Creates sample files for:
- pothole.jpg
- garbage.jpg
- streetlight.jpg
- waterlogging.jpg
- non_civic.jpg
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DATA_SAMPLES = Path(__file__).resolve().parent / "data" / "samples"
DATA_SAMPLES.mkdir(parents=True, exist_ok=True)


def create_sample_image(filename: str, bg_color: tuple, title: str, subtitle: str, elements_drawer=None):
    img = Image.new("RGB", (640, 480), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw decorative elements
    if elements_drawer:
        elements_drawer(draw)

    # Banner overlay
    draw.rectangle([20, 20, 620, 90], fill=(16, 42, 67, 230), outline=(244, 163, 64), width=2)
    draw.text((40, 32), f"NAZARSETU DEMO SAMPLE: {title}", fill=(255, 255, 255))
    draw.text((40, 60), subtitle, fill=(244, 163, 64))

    out_path = DATA_SAMPLES / filename
    img.save(out_path, format="JPEG", quality=90)
    print(f"Generated {out_path}")


def draw_pothole(draw):
    # Road surface
    draw.rectangle([0, 100, 640, 480], fill=(60, 64, 67))
    # Lane marking
    for x in range(40, 600, 80):
        draw.rectangle([x, 260, x + 40, 275], fill=(240, 240, 240))
    # Dark crater pothole
    draw.ellipse([180, 290, 460, 430], fill=(25, 25, 28), outline=(120, 80, 50), width=6)
    # Inner cracks and water/rocks
    draw.ellipse([220, 320, 420, 400], fill=(15, 15, 18))
    draw.line([180, 350, 120, 380], fill=(20, 20, 20), width=3)
    draw.line([460, 350, 520, 390], fill=(20, 20, 20), width=3)


def draw_garbage(draw):
    # Pavement background
    draw.rectangle([0, 100, 640, 480], fill=(180, 185, 190))
    # Green municipal bin
    draw.rectangle([220, 200, 420, 420], fill=(34, 139, 34), outline=(20, 80, 20), width=4)
    # Overflowing trash pile
    draw.ellipse([160, 160, 480, 260], fill=(210, 180, 140))
    draw.polygon([(180, 320), (140, 440), (240, 440)], fill=(70, 130, 180)) # Blue plastic bag
    draw.polygon([(380, 330), (460, 450), (360, 450)], fill=(220, 20, 60)) # Red bag
    draw.ellipse([280, 360, 380, 440], fill=(245, 222, 179)) # Cardboard


def draw_streetlight(draw):
    # Night sky
    draw.rectangle([0, 100, 640, 480], fill=(15, 23, 42))
    # Street lamp post
    draw.rectangle([295, 150, 315, 480], fill=(100, 116, 139))
    # Lamp arm and fixture
    draw.line([305, 180, 420, 140], fill=(100, 116, 139), width=8)
    draw.rectangle([380, 140, 450, 170], fill=(71, 85, 105), outline=(148, 163, 184), width=2)
    # Extinguished/broken indicator
    draw.ellipse([395, 170, 435, 190], fill=(30, 41, 59))
    draw.text((360, 200), "⚡ DARK FIXTURE / DEFECTIVE BULB", fill=(239, 68, 68))


def draw_waterlogging(draw):
    # Flooded street
    draw.rectangle([0, 100, 640, 480], fill=(71, 85, 105))
    # Deep murky flood water
    draw.rectangle([0, 240, 640, 480], fill=(51, 65, 85))
    # Ripples
    for y in range(270, 460, 35):
        draw.arc([100, y, 540, y + 25], start=0, end=180, fill=(148, 163, 184), width=3)
    # Submerged curb
    draw.line([0, 240, 640, 240], fill=(203, 213, 225), width=4)


def draw_non_civic(draw):
    # Warm indoor living room background
    draw.rectangle([0, 100, 640, 480], fill=(254, 243, 199))
    # Houseplant / domestic pet illustration
    draw.ellipse([260, 220, 380, 340], fill=(217, 119, 6)) # Pet cat shape
    draw.polygon([(270, 230), (290, 180), (310, 230)], fill=(217, 119, 6)) # Ear
    draw.polygon([(330, 230), (350, 180), (370, 230)], fill=(217, 119, 6)) # Ear
    draw.ellipse([290, 250, 310, 270], fill=(30, 41, 59)) # Eye
    draw.ellipse([330, 250, 350, 270], fill=(30, 41, 59)) # Eye
    draw.text((220, 380), "[ INDOOR DOMESTIC PET - NON-CIVIC ]", fill=(180, 83, 9))


if __name__ == "__main__":
    create_sample_image("sample_pothole.jpg", (40, 40, 40), "POTHOLE & CRACKED ROAD", "Severe asphalt crater on arterial corridor", draw_pothole)
    create_sample_image("sample_garbage.jpg", (200, 200, 200), "OVERFLOWING GARBAGE", "Uncollected municipal refuse spilling on sidewalk", draw_garbage)
    create_sample_image("sample_streetlight.jpg", (15, 23, 42), "BROKEN STREETLIGHT", "Non-operational pole lighting fixture at night", draw_streetlight)
    create_sample_image("sample_waterlogging.jpg", (50, 60, 70), "WATERLOGGED STREET", "Stagnant stormwater inundation over pedestrian walkway", draw_waterlogging)
    create_sample_image("sample_non_civic.jpg", (255, 250, 240), "NON-CIVIC PHOTOGRAPH", "Indoor domestic scene (Pet cat) - Unsupported", draw_non_civic)
