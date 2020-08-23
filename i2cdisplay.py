import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

class display:
	def __init__(self):
		self.textfield = 'Aquarium Monitor'
		self.oled_reset = 24
		self.WIDTH = 128
		self.HEIGHT = 64
		self.BORDER = 5
		self.i2c = board.I2C()
		self.oled = adafruit_ssd1306.SSD1306_I2C(self.WIDTH, self.HEIGHT, self.i2c, addr=0x3c) #reset taken out

	def drawStatus(self, text1, text2):
		self.oled.fill(0)
		self.oled.show()

		# Create blank image for drawing.
		# Make sure to create image with mode '1' for 1-bit color.
		image = Image.new('1', (self.oled.width, self.oled.height))

		# Get drawing object to draw on image.
		draw = ImageDraw.Draw(image)

		# Draw a white background
		draw.rectangle((0, 0, self.oled.width, self.oled.height), outline=255, fill=255)

		# Draw a smaller inner rectangle
		draw.rectangle((self.BORDER, self.BORDER, self.oled.width - self.BORDER - 1, self.oled.height - self.BORDER - 1), outline=0, fill=0)

		# Load default font.
		font = ImageFont.load_default()

		# Draw Some Text
		text1 = text1
		(font_width, font_height) = font.getsize(text1)
		draw.text((self.oled.width//2 - font_width//2, self.oled.height//2 - font_height//2), text1, font=font, fill=255)

		text2 = text2
		(font_width, font_height) = font.getsize(text1)
		draw.text((self.oled.width//4 - font_width//2, self.oled.height//4 - font_height//2), text2, font=font, fill=255)


		# Display image
		self.oled.image(image)
		self.oled.show()

'''
# Define the Reset Pin
oled_reset = 24

# Change these
# to the right size for your display!
WIDTH = 128
HEIGHT = 64     # Change to 64 if needed
BORDER = 5

# Use for I2C.
i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3c, reset=oled_reset)

# Clear display.
oled.fill(0)
oled.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new('1', (oled.width, oled.height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a white background
draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

# Draw a smaller inner rectangle
draw.rectangle((BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1), outline=0, fill=0)

# Load default font.
font = ImageFont.load_default()

# Draw Some Text
text = "Drawing water"
(font_width, font_height) = font.getsize(text)
draw.text((oled.width//2 - font_width//2, oled.height//2 - font_height//2), text, font=font, fill=255)

# Display image
oled.image(image)
oled.show()

'''