# 베이스 이미지
FROM python:3.9-slim

# 작업 디렉터리 생성
WORKDIR /app

# requirements.txt 복사
COPY requirements.txt /app/

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . /app/

# Flask 애플리케이션 실행
CMD ["python", "dice_roll.py"]
