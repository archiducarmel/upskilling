from flask import Flask, render_template_string
import os

app = Flask(__name__)

# Template HTML simple
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mon App Flask - Domino</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 { color: #2c3e50; }
        .info { color: #7f8c8d; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Application Flask sur Domino Data Lab</h1>
        <p>Bienvenue ! Cette application fonctionne correctement.</p>
        <div class="info">
            <p><strong>Environnement :</strong> {{ env }}</p>
            <p><strong>Port :</strong> {{ port }}</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    env = os.environ.get('DOMINO_PROJECT_NAME', 'Local')
    port = os.environ.get('PORT', '8888')
    return render_template_string(HTML_TEMPLATE, env=env, port=port)

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    # Domino utilise la variable d'environnement PORT ou 8888 par défaut
    port = int(os.environ.get('PORT', 8888))
    app.run(host='0.0.0.0', port=port, debug=False)
