#!/bin/bash
# run_tests.sh: Comprehensive test runner for InfoBlox WAPI NLP system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "FAIL")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${YELLOW}ℹ${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$(basename $test_file .py)
    
    print_status "INFO" "Running $test_name..."
    
    if python3 "$test_file" -v 2>&1 | tee /tmp/${test_name}.log; then
        print_status "SUCCESS" "$test_name completed successfully"
        ((TESTS_PASSED++))
        return 0
    else
        print_status "FAIL" "$test_name failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Main test execution
main() {
    echo "========================================="
    echo "InfoBlox WAPI NLP System - Test Suite"
    echo "========================================="
    echo ""
    
    # Check Python installation
    print_status "INFO" "Checking Python environment..."
    if ! command -v python3 &>/dev/null; then
        print_status "FAIL" "Python 3 is not installed"
        exit 1
    fi
    
    python_version=$(python3 --version 2>&1)
    print_status "SUCCESS" "Found $python_version"
    
    # Check for required modules (without full environment setup for basic tests)
    print_status "INFO" "Checking Python modules..."
    required_modules=("unittest" "json" "tempfile")
    
    for module in "${required_modules[@]}"; do
        if python3 -c "import $module" 2>/dev/null; then
            print_status "SUCCESS" "Module '$module' available"
        else
            print_status "FAIL" "Module '$module' not found"
            ((TESTS_SKIPPED++))
        fi
    done
    
    echo ""
    echo "========================================="
    echo "Running Unit Tests"
    echo "========================================="
    echo ""
    
    # Run NLP processing tests
    if [ -f "tests/test_nlp_processing.py" ]; then
        run_test "tests/test_nlp_processing.py" || true
    else
        print_status "FAIL" "test_nlp_processing.py not found"
        ((TESTS_SKIPPED++))
    fi
    
    echo ""
    echo "========================================="
    echo "Running Integration Tests"  
    echo "========================================="
    echo ""
    
    # Run WAPI integration tests
    if [ -f "tests/test_wapi_integration.py" ]; then
        run_test "tests/test_wapi_integration.py" || true
    else
        print_status "FAIL" "test_wapi_integration.py not found"
        ((TESTS_SKIPPED++))
    fi
    
    echo ""
    echo "========================================="
    echo "Running API Tests"
    echo "========================================="
    echo ""
    
    # Run Flask API tests
    if [ -f "tests/test_flask_api.py" ]; then
        # Check if Flask is available
        if python3 -c "import flask" 2>/dev/null; then
            run_test "tests/test_flask_api.py" || true
        else
            print_status "INFO" "Flask not installed, skipping API tests"
            ((TESTS_SKIPPED++))
        fi
    else
        print_status "FAIL" "test_flask_api.py not found"
        ((TESTS_SKIPPED++))
    fi
    
    echo ""
    echo "========================================="
    echo "Configuration Tests"
    echo "========================================="
    echo ""
    
    # Test setup.sh script syntax
    print_status "INFO" "Checking setup.sh syntax..."
    if bash -n setup.sh 2>/dev/null; then
        print_status "SUCCESS" "setup.sh syntax is valid"
        ((TESTS_PASSED++))
    else
        print_status "FAIL" "setup.sh has syntax errors"
        ((TESTS_FAILED++))
    fi
    
    # Check if Docker is installed (for integration)
    print_status "INFO" "Checking Docker installation..."
    if command -v docker &>/dev/null; then
        docker_version=$(docker --version 2>&1)
        print_status "SUCCESS" "Found $docker_version"
        
        # Check if Docker is running
        if docker info &>/dev/null; then
            print_status "SUCCESS" "Docker daemon is running"
        else
            print_status "INFO" "Docker daemon not running (tests will skip Docker operations)"
        fi
    else
        print_status "INFO" "Docker not installed (integration tests will be limited)"
    fi
    
    echo ""
    echo "========================================="
    echo "Security Tests"
    echo "========================================="
    echo ""
    
    # Check for hardcoded credentials
    print_status "INFO" "Checking for hardcoded credentials..."
    if grep -q "PASSWORD.*=.*InfoBlox" setup.sh; then
        print_status "INFO" "Warning: Hardcoded password found in setup.sh"
    else
        print_status "SUCCESS" "No obvious hardcoded passwords found"
    fi
    
    # Check for sensitive file permissions
    print_status "INFO" "Checking file permissions..."
    if [ -f "grok_config.json" ]; then
        perms=$(stat -f "%A" grok_config.json 2>/dev/null || stat -c "%a" grok_config.json 2>/dev/null || echo "unknown")
        if [ "$perms" != "unknown" ] && [ "$perms" -le 600 ]; then
            print_status "SUCCESS" "grok_config.json has restrictive permissions"
        else
            print_status "INFO" "Consider restricting grok_config.json permissions (chmod 600)"
        fi
    fi
    
    echo ""
    echo "========================================="
    echo "Code Quality Checks"
    echo "========================================="
    echo ""
    
    # Check Python files for basic issues
    print_status "INFO" "Running Python syntax checks..."
    for py_file in tests/*.py; do
        if [ -f "$py_file" ]; then
            if python3 -m py_compile "$py_file" 2>/dev/null; then
                print_status "SUCCESS" "$(basename $py_file) syntax valid"
            else
                print_status "FAIL" "$(basename $py_file) has syntax errors"
                ((TESTS_FAILED++))
            fi
        fi
    done
    
    echo ""
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    echo ""
    
    total_tests=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    
    print_status "INFO" "Total Tests: $total_tests"
    print_status "SUCCESS" "Passed: $TESTS_PASSED"
    [ $TESTS_FAILED -gt 0 ] && print_status "FAIL" "Failed: $TESTS_FAILED"
    [ $TESTS_SKIPPED -gt 0 ] && print_status "INFO" "Skipped: $TESTS_SKIPPED"
    
    echo ""
    
    # Generate test report
    report_file="test_report_$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "InfoBlox WAPI NLP System - Test Report"
        echo "Generated: $(date)"
        echo ""
        echo "Summary:"
        echo "  Total Tests: $total_tests"
        echo "  Passed: $TESTS_PASSED"
        echo "  Failed: $TESTS_FAILED"
        echo "  Skipped: $TESTS_SKIPPED"
        echo ""
        echo "Details:"
        
        for log_file in /tmp/test_*.log; do
            if [ -f "$log_file" ]; then
                echo ""
                echo "--- $(basename $log_file .log) ---"
                tail -n 20 "$log_file"
            fi
        done
    } > "$report_file"
    
    print_status "INFO" "Test report saved to $report_file"
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"