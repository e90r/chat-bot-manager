import uvicorn

from app.db_utils import init_db
from app.factory import create_app

if __name__ == '__main__':
    app = create_app()
    init_db()
    uvicorn.run(app, host='0.0.0.0', port=8000)
