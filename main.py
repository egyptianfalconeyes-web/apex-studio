from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)

# تصميم واجهة الاستوديو بتنسيق Cyberpunk / Glassmorphism الحديث والمتوافق مع كافة المتصفحات
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المبتكرون العرب - Apex AI Studio</title>
    <style>
        :root {
            --bg-color: #0d0f18;
            --panel-bg: rgba(20, 24, 39, 0.75);
            --accent-neon: #00ffcc;
            --accent-purple: #9d4edd;
            --text-main: #f8f9fa;
        }
        body {
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .studio-container {
            width: 90%;
            max-width: 800px;
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.2);
            border-radius: 16px;
            box-shadow: 0 0 30px rgba(0, 255, 204, 0.1);
            padding: 30px;
            box-sizing: border-box;
        }
        h1 {
            text-align: center;
            color: var(--accent-neon);
            text-shadow: 0 0 10px rgba(0, 255, 204, 0.4);
            margin-bottom: 10px;
        }
        p.subtitle {
            text-align: center;
            color: #a0aec0;
            margin-bottom: 30px;
        }
        .control-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: var(--accent-neon);
            font-weight: bold;
        }
        textarea, input {
            width: 100%;
            padding: 12px;
            background: rgba(10, 12, 20, 0.8);
            border: 1px solid #2d3748;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            box-sizing: border-box;
        }
        textarea:focus, input:focus {
            border-color: var(--accent-neon);
            outline: none;
            box-shadow: 0 0 8px rgba(0, 255, 204, 0.3);
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, var(--accent-neon), var(--accent-purple));
            border: none;
            border-radius: 8px;
            color: #0d0f18;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.3s ease;
            margin-top: 10px;
        }
        button:hover {
            opacity: 0.9;
        }
        .output-box {
            margin-top: 25px;
            padding: 15px;
            background: rgba(0, 0, 0, 0.5);
            border-left: 4px solid var(--accent-neon);
            border-radius: 4px;
            min-height: 50px;
            word-break: break-word;
        }
    </style>
</head>
<body>
    <div class="studio-container">
        <h1>المبتكرون العرب - Apex Studio</h1>
        <p class="subtitle">منظومة الذكاء الاصطناعي الشاملة للإنتاج السينمائي والصوتي</p>
        
        <div class="control-group">
            <label for="prompt">أدخل وصف المشروع أو النص السينمائي:</label>
            <textarea id="prompt" rows="4" placeholder="اكتب وصف الإعلان أو الفيديو هنا..."></textarea>
        </div>
        
        <button onclick="runStudio()">بدء المعالجة والإنتاج</button>
        
        <div class="output-box" id="output">المنظومة جاهزة للعمل...</div>
    </div>

    <script>
        function runStudio() {
            const promptText = document.getElementById('prompt').value;
            const outputDiv = document.getElementById('output');
            
            if(!promptText.trim()) {
                outputDiv.innerHTML = "الرجاء إدخال وصف صحيح أولاً.";
                return;
            }
            
            outputDiv.innerHTML = "جاري المعالجة وتوليد العناصر عبر الذكاء الاصطناعي...";
            
            fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: promptText })
            })
            .then(res => res.json())
            .then(data => {
                outputDiv.innerHTML = "<strong>النتيجة:</strong> " + data.result;
            })
            .catch(err => {
                outputDiv.innerHTML = "حدث خطأ أثناء الاتصال بالخادم المحلي.";
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    user_prompt = data.get('prompt', '')
    # معالجة افتراضية مستقرة لتجنب أي أخطاء برمجية
    response_msg = f"تم استلام طلبك بنجاح وجاري إعداد أصول الإنتاج لـ: '{user_prompt}'"
    return jsonify({'result': response_msg})

if __name__ == '__main__':
    # التشغيل على المنفذ المحلي ليعمل بسلاسة تامة على الكمبيوتر
    app.run(host='0.0.0.0', port=5000, debug=False)
