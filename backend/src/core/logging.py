"""앱 전체 로그 형식 설정. main.py 에서 앱을 만들기 전에 한 번 호출해요."""
import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    # gourmand.* 로거만 설정해서 uvicorn 기본 로그와 겹치지 않게 해요
    logger = logging.getLogger("gourmand")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
