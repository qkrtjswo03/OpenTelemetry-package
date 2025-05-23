from flask import Flask, jsonify
import random

app = Flask(__name__)

@app.route('/roll', methods=['GET'])
def roll_dice():
    # 1에서 6까지의 숫자 중 랜덤으로 선택
    result = random.randint(1, 6)
    return jsonify({"dice_roll": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
