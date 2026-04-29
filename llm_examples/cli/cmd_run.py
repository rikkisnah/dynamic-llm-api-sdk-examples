"""Tier 5: `run` command handler."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from llm_examples.cli.output import print_json, print_lines
from llm_examples.cli.providers import resolve_provider
from llm_examples.domain_types import LLMError, ProviderName
from llm_examples.services import run_prompt, stream_prompt


def handle_run(args: Namespace) -> int:
    """Run prompt call, optionally in streaming mode."""
    provider = resolve_provider(args.provider)
    prompt = _resolve_prompt(provider, args.prompt, args.prompt_file)
    if args.stream:
        stream_result = stream_prompt(
            provider=provider,
            model=args.model,
            prompt=prompt,
            system=args.system,
            max_tokens=args.max_tokens,
        )
        chunks = list(stream_result.chunks)
        text = "".join(chunks)
        if args.json:
            print_json(
                {
                    "ok": True,
                    "provider": stream_result.provider,
                    "model": stream_result.model,
                    "stream": True,
                    "simulated_stream": stream_result.simulated,
                    "text": text,
                    "chunks": chunks,
                }
            )
        else:
            for chunk in chunks:
                sys.stdout.write(chunk)
                sys.stdout.flush()
            sys.stdout.write("\n")
            if stream_result.simulated:
                print_lines(["[simulated stream]"])
        return 0

    response = run_prompt(
        provider=provider,
        model=args.model,
        prompt=prompt,
        system=args.system,
        max_tokens=args.max_tokens,
    )
    if args.json:
        print_json(
            {
                "ok": True,
                "provider": response.provider,
                "model": response.model,
                "text": response.text,
                "latency_ms": response.latency_ms,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None,
                "raw_id": response.raw_id,
            }
        )
    else:
        print_lines([response.text, f"latency_ms={response.latency_ms:.1f}"])
    return 0


def _resolve_prompt(provider: ProviderName, prompt: str | None, prompt_file: str | None) -> str:
    if prompt and prompt_file:
        raise LLMError(
            provider=provider,
            model=None,
            kind="bad_request",
            message="Use either --prompt or --prompt-file, not both.",
        )
    if prompt is not None:
        return prompt
    if prompt_file is None:
        raise LLMError(
            provider=provider,
            model=None,
            kind="bad_request",
            message="You must provide --prompt or --prompt-file.",
        )
    if prompt_file == "-":
        return sys.stdin.read()
    return Path(prompt_file).read_text(encoding="utf-8")
