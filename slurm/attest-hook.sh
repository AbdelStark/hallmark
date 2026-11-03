#!/bin/bash
#
# Optional confidential computing attestation hook
#
# This script computes a manifest hash for attestation but does NOT execute
# privileged attestation tools automatically. Users must explicitly integrate
# attestation commands into their workflow after reviewing security requirements.
#
# Usage: ./attest-hook.sh <output-dir> <input-hashes-file> <binary-hashes-file> <proof-hashes-file> <verifier-nonce>

set -euo pipefail

if [ $# -lt 5 ]; then
    cat <<EOF
Usage: $0 <output-dir> <input-hashes-file> <binary-hashes-file> <proof-hashes-file> <verifier-nonce>

Computes attestation manifest hash from:
  - Input archive hashes
  - Binary hashes (prover executables)
  - Proof hashes
  - Verifier-supplied nonce

Outputs:
  - manifest-hash.txt: 64-character hex hash for attestation
  - attest-commands.sh: Example attestation commands (NOT executed)

This script does NOT execute attestation tools. Users must:
1. Review security requirements
2. Obtain appropriate permissions
3. Manually execute attestation commands from attest-commands.sh
4. Verify attestation results independently
EOF
    exit 1
fi

OUTPUT_DIR="$1"
INPUT_HASHES="$2"
BINARY_HASHES="$3"
PROOF_HASHES="$4"
VERIFIER_NONCE="$5"

mkdir -p "$OUTPUT_DIR"

echo "=== Computing Attestation Manifest Hash ==="
echo "Input hashes: $INPUT_HASHES"
echo "Binary hashes: $BINARY_HASHES"
echo "Proof hashes: $PROOF_HASHES"
echo "Verifier nonce: $VERIFIER_NONCE"

# Compute manifest hash
MANIFEST_HASH=$(cat \
    "$INPUT_HASHES" \
    "$BINARY_HASHES" \
    "$PROOF_HASHES" \
    <(echo "$VERIFIER_NONCE") \
    | sha256sum | cut -d' ' -f1)

echo ""
echo "Manifest hash: $MANIFEST_HASH"
echo "$MANIFEST_HASH" > "$OUTPUT_DIR/manifest-hash.txt"

# Generate example attestation commands
cat > "$OUTPUT_DIR/attest-commands.sh" <<EOF
#!/bin/bash
# Example attestation commands - DO NOT EXECUTE WITHOUT REVIEW
#
# These commands require:
# - Appropriate node permissions
# - Privileged access to attestation tools
# - Security review and approval
#
# Users must verify tool availability and syntax for their environment.

set -euo pipefail

MANIFEST_HASH="$MANIFEST_HASH"
OUTPUT_DIR="$OUTPUT_DIR"

echo "=== Attestation Commands (MANUAL EXECUTION REQUIRED) ==="
echo ""
echo "1. TDX Quote Generation (requires sudo, CPU-only job step):"
echo "   sudo -n tdx-quote \$MANIFEST_HASH > \$OUTPUT_DIR/tdx-quote.bin"
echo ""
echo "   Optional: Dump CCEL event log:"
echo "   sudo -n tdx-quote --event-log \$MANIFEST_HASH > \$OUTPUT_DIR/tdx-quote-events.bin"
echo ""
echo "2. NVIDIA GPU Attestation (check nvattest version for nonce option):"
echo "   nvattest attest --device gpu --verifier local > \$OUTPUT_DIR/gpu-attest-local.json"
echo ""
echo "   Or with remote verifier:"
echo "   nvattest attest --device gpu --verifier remote > \$OUTPUT_DIR/gpu-attest-remote.json"
echo ""
echo "   Note: nvattest nonce option syntax depends on installed version."
echo "   Consult NVIDIA nvattest documentation for your specific driver version."
echo ""
echo "3. After attestation, append results to run-record.json:"
echo "   # Add attestation fields to run record manually"
echo ""
echo "IMPORTANT: Review security requirements before executing any attestation commands."
EOF

chmod +x "$OUTPUT_DIR/attest-commands.sh"

echo ""
echo "=== Output ==="
echo "Manifest hash: $OUTPUT_DIR/manifest-hash.txt"
echo "Commands: $OUTPUT_DIR/attest-commands.sh"
echo ""
echo "Review and manually execute attestation commands as appropriate."
echo "DO NOT run attestation tools without proper authorization and security review."
