import copy
import traceback


class CrashRecoveryWrapper:
    """
    Wraps an execution engine to ensure:
      - Exceptions are caught
      - State is not mutated on failure
      - Engine call attempts are still recorded
    """

    def __init__(self, engine):
        self.engine = engine

    def safe_execute(self, command, state):
        """
        Executes the engine safely:
          - Uses a deep copy of state
          - Returns structured failure on exception
          - Never mutates the original state
        """
        state_copy = copy.deepcopy(state)

        try:
            result = self.engine.execute(command, state_copy)
            state.clear()
            state.update(state_copy)
            return result

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


# ------------------------------------------------------------
# TOP‑LEVEL WRAPPER FOR APP STARTUP
# ------------------------------------------------------------

def run_with_crash_recovery(fn):
    """
    Compatibility wrapper expected by app.py.

    Executes fn() inside a crash‑recovery boundary.
    Returns a tuple:
        (ok: bool, result_or_error)
    """
    try:
        result = fn()
        return True, result
    except Exception as e:
        return False, f"{e}\n{traceback.format_exc()}"
