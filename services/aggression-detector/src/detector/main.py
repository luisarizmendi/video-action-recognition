import threading

from .app import create_app, gate_loop

_stop = threading.Event()
threading.Thread(target=gate_loop, args=(_stop,), daemon=True).start()
app = create_app()
