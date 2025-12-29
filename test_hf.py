#!/usr/bin/env python3
"""Test script to debug Hugging Face API connection"""

import os
from healthllm.sqlgen_hf import hf_config_from_env, generate_sql_hf, HuggingFaceSqlGenError

# Get token from environment variable (set it before running: export HF_TOKEN='hf_...')
# For testing, you can set it here temporarily, but DO NOT commit this file with a real token!
if not os.getenv('HF_TOKEN'):
    print("ERROR: HF_TOKEN environment variable not set!")
    print("Set it with: export HF_TOKEN='hf_your_token_here'")
    exit(1)

# Model can be set via environment or use default
if not os.getenv('HF_MODEL'):
    os.environ['HF_MODEL'] = 'deepseek-ai/DeepSeek-V3.2:novita'

print("Testing Hugging Face connection...")
print(f"Token set: {bool(os.getenv('HF_TOKEN'))}")
print(f"Token starts with: {os.getenv('HF_TOKEN', '')[:10]}...")
print(f"Model: {os.getenv('HF_MODEL', 'not set')}")
print()

cfg = hf_config_from_env()
if not cfg:
    print("ERROR: Could not create HF config from environment")
    exit(1)

print(f"HF Config created successfully")
print(f"  Token: {cfg.token[:10]}...")
print(f"  Model: {cfg.model}")
print()

test_question = "How many steps did I walk this year?"
print(f"Testing with question: '{test_question}'")
print()

try:
    sql = generate_sql_hf(test_question, cfg)
    print("SUCCESS!")
    print(f"Generated SQL: {sql}")
except HuggingFaceSqlGenError as e:
    print("ERROR occurred:")
    print(f"  {type(e).__name__}: {str(e)}")
    print()
    print("This is the error that's causing the fallback to templates.")
except Exception as e:
    print(f"Unexpected error: {type(e).__name__}: {str(e)}")

