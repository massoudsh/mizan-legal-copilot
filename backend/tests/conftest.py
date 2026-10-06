import os
import tempfile

os.environ["MIZAN_DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
