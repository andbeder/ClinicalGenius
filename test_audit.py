#!/usr/bin/env python3
"""Test audit logging system"""

from audit_logger import get_audit_logger, AuditLogger
import json

# Get audit logger
logger = get_audit_logger()

print("Testing Audit Logging System")
print("=" * 60)
print()

# Test 1: Log PHI access
print("Test 1: Logging PHI access event...")
logger.log_phi_access(
    dataset_id="test_dataset_123",
    record_count=50,
    action="read",
    metadata={'test': True}
)
print("✓ PHI access logged")
print()

# Test 2: Log batch execution
print("Test 2: Logging batch execution...")
logger.log_batch_execution(
    batch_id="test_batch_456",
    batch_name="Test Batch",
    dataset_id="test_dataset_123",
    record_count=100,
    success=True,
    metadata={'execution_time': 45.2}
)
print("✓ Batch execution logged")
print()

# Test 3: Log access denied
print("Test 3: Logging access denied...")
logger.log_access_denied(
    reason="Test access denial",
    ip_address="192.168.1.100"
)
print("✓ Access denied logged")
print()

# Test 4: Log LLM request
print("Test 4: Logging LLM request...")
logger.log_llm_request(
    provider="openai",
    model="gpt-4o-mini",
    record_id="test_record_789",
    success=True
)
print("✓ LLM request logged")
print()

# Retrieve and display recent logs
print("=" * 60)
print("Recent Audit Log Entries:")
print("=" * 60)
logs = logger.get_recent_logs(10)

for i, log in enumerate(logs, 1):
    print(f"\n{i}. Event Type: {log['event_type']}")
    print(f"   Timestamp: {log['timestamp']}")
    print(f"   Action: {log['action']}")
    print(f"   Success: {'Yes' if log['success'] else 'No'}")
    if log['dataset_id']:
        print(f"   Dataset: {log['dataset_id']}")
    if log['record_count']:
        print(f"   Records: {log['record_count']}")
    if log['metadata'] and log['metadata'] != '{}':
        metadata = json.loads(log['metadata'])
        print(f"   Metadata: {metadata}")

print()
print("=" * 60)
print(f"✓ Test complete - {len(logs)} audit entries created")
print("=" * 60)
