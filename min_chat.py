"""min_chat.config — a composition root.

This file is the only place that knows both module names. It is not a fourth
artifact: it has no behaviour, no branches, no rules. It names parts and hands
them to the runtime. The moment a config contains a decision, cross-artifact
coupling has found somewhere to live and the diagonal is back in disguise.

The pairing it asserts is verified by Runtime.compose() at boot, before
ignition, and fails closed.
"""

from __future__ import annotations

from environment.ui_dialog import DialogEnvironment
from framework.min_chat import ChatFramework
from model.chat_stub import ChatModel
from runtime import Objective, Runtime

FRAMEWORK_MODULE = "min_chat-mode"
ENVIRONMENT_MODULE = "ui-dialogwin-io"


def assemble(prompt: str, budget: int = 12) -> tuple[Runtime, DialogEnvironment]:
    environment = DialogEnvironment(prompt=prompt)
    runtime = Runtime(
        framework=ChatFramework(),
        environment=environment,
        model=ChatModel(),
        objective=Objective("chat-0001", "answer one prompt", budget),
    )
    return runtime, environment
