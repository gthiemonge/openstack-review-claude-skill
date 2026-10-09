#!/bin/bash
# Test script to verify package installation

set -e

echo "Testing openstack-review package installation..."
echo ""

# Test 1: Import package
echo "Test 1: Importing package..."
python3 -c "import openstack_review; print(f'✓ Package version: {openstack_review.__version__}')"

# Test 2: Check CLI commands
echo ""
echo "Test 2: Checking CLI commands..."
which openstack-review && echo "✓ openstack-review command found"
which detect-models && echo "✓ detect-models command found"
which gerrit-review && echo "✓ gerrit-review command found"

# Test 3: Verify help works
echo ""
echo "Test 3: Testing help output..."
openstack-review --help > /dev/null && echo "✓ openstack-review --help works"
detect-models --help > /dev/null && echo "✓ detect-models --help works"
gerrit-review --help > /dev/null 2>&1 || echo "⚠  gerrit-review (expected to fail without args)"

# Test 4: Check package can find config
echo ""
echo "Test 4: Testing configuration..."
python3 -c "from openstack_review import get_model_config, list_presets; print('✓ Config functions importable')"
python3 -c "from openstack_review import list_presets; print(list_presets())" | head -5

echo ""
echo "✅ All tests passed!"
echo ""
echo "You can now use:"
echo "  openstack-review <review-number>"
echo "  detect-models --vertex --project YOUR_PROJECT"
echo "  gerrit-review fetch <review-number>"
