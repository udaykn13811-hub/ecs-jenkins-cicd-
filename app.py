from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = "Version 1"

@app.route("/")
def home():
    return jsonify({
        "application": "AA Software Technologies",
        "message": "ECS CI/CD Pipeline using Jenkins",
        "version": APP_VERSION
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
