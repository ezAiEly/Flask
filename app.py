from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # 获取表单数据
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        # 这里可以保存到数据库或发送邮件
        print("=" * 50)
        print(f"Received message：{message}")
        print(f"Form：{name} - {email}")
        print("=" * 50)
        return render_template('contact.html', success=True)
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)