import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join('/opt/signature-tool/data', 'signatures.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/opt/signature-tool/data/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    DATA_DIR = os.environ.get('DATA_DIR', '/opt/signature-tool/data')
    GENERATED_DIR = os.environ.get('GENERATED_DIR', '/opt/signature-tool/data/generated')
    DEFAULT_LANG = os.environ.get('DEFAULT_LANG', 'en')  # 'en' or 'de'
