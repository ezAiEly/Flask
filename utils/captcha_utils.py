import random
import string
import base64
import io
from captcha.image import ImageCaptcha

image_captcha = ImageCaptcha(width=160, height=60, font_sizes=(40, 44, 48))


def generate_captcha():
    chars = ''.join(c for c in string.ascii_uppercase + string.digits if c not in 'O0I1L')
    answer = ''.join(random.choices(chars, k=4))
    img_data = image_captcha.generate(answer)
    img_bytes = img_data.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode()
    return img_base64, answer.lower()
