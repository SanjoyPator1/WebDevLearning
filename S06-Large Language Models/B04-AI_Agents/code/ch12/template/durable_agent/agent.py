import argparse
import json
import os
import sys


def append_event(log_path, event):
    # Notes Section 2: the event-history log IS the source of truth, not live process memory.
    with open(log_path, "a") as f:
        f.write(json.dumps(event) + "\n")


def read_completed_steps(log_path):
    # Deterministic replay input: which steps does the log say already happened?
    if not os.path.exists(log_path):
        return set()
    completed = set()
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("status") == "completed":
                completed.add(event["step"])
    return completed


def send_email(to, idempotency_key, sent_log_path):
    # Notes Section 4: check the idempotency key BEFORE the real effect, not after.
    sent_keys = set()
    if os.path.exists(sent_log_path):
        with open(sent_log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    sent_keys.add(json.loads(line)["key"])

    if idempotency_key in sent_keys:
        return f"ALREADY_SENT (idempotent no-op) key={idempotency_key}"

    # The real, side-effecting action -- this only ever happens once per key.
    result = f"Email actually sent to {to}"
    with open(sent_log_path, "a") as f:
        f.write(json.dumps({"key": idempotency_key, "to": to}) + "\n")
    return result


def run_durable(n_steps, event_log_path, sent_log_path, email_step, crash_after_step, crash_after_send_before_log):
    completed = read_completed_steps(event_log_path)
    executed = []
    for step in range(1, n_steps + 1):
        if step in completed:
            continue  # trust the log -- do NOT redo real work for an already-completed step

        executed.append(step)
        if step == email_step:
            result = send_email("user@example.com", idempotency_key=f"welcome-email-step-{step}", sent_log_path=sent_log_path)
            print(f"step {step}: {result}")
            if step == crash_after_send_before_log:
                sys.stdout.flush()
                os._exit(1)  # hard crash AFTER the real send, BEFORE this step is recorded complete
        else:
            print(f"step {step}: did work")

        append_event(event_log_path, {"step": step, "status": "completed"})
        if step == crash_after_step:
            sys.stdout.flush()
            os._exit(1)  # hard crash right after this step's own checkpoint was durably written

    print(f"RUN_COMPLETE executed_steps={executed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-steps", type=int, default=60)
    parser.add_argument("--event-log", required=True)
    parser.add_argument("--sent-log", required=True)
    parser.add_argument("--email-step", type=int, default=45)
    parser.add_argument("--crash-after-step", type=int, default=None)
    parser.add_argument("--crash-after-send-before-log", type=int, default=None)
    args = parser.parse_args()
    run_durable(args.n_steps, args.event_log, args.sent_log, args.email_step,
                args.crash_after_step, args.crash_after_send_before_log)
