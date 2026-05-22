import io
import base64
from flask import Blueprint, render_template, request, send_file, jsonify, url_for, current_app
from PIL import Image
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import SquareModuleDrawer, GappedSquareModuleDrawer, RoundedModuleDrawer

qrcode_bp = Blueprint('qrcode', __name__)


@qrcode_bp.route('/qrcode-generator')
def qrcode_page():
    return render_template('qrcode.html')


@qrcode_bp.route('/api/qrcode')
def generate_qrcode():
    text = request.args.get('text', '').strip()
    if not text:
        return jsonify({'error': '请输入文本或URL'}), 400

    logo = request.args.get('logo', 'false').lower() == 'true'
    style = request.args.get('style', 'square')  # square, gapped, rounded
    fg_color = request.args.get('fg', '#000000')
    bg_color = request.args.get('bg', '#FFFFFF')

    fg = tuple(int(fg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    bg = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    drawer_map = {
        'square': SquareModuleDrawer(),
        'gapped': GappedSquareModuleDrawer(),
        'rounded': RoundedModuleDrawer(),
    }
    module_drawer = drawer_map.get(style, SquareModuleDrawer())

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H if logo else qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        color_mask=SolidFillColorMask(back_color=bg, front_color=fg),
    ).convert('RGBA')

    if logo:
        logo_size = min(img.size) // 5
        logo_path = current_app.config.get('QR_LOGO_PATH', 'static/images/default-avatar.GIF')
        try:
            logo_img = Image.open(logo_path).convert('RGBA')
            logo_img.thumbnail((logo_size, logo_size), Image.LANCZOS)
            pos = ((img.size[0] - logo_img.size[0]) // 2, (img.size[1] - logo_img.size[1]) // 2)
            img.paste(logo_img, pos, logo_img)
        except Exception:
            pass  # Logo optional

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')
