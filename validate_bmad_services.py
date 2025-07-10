#!/usr/bin/env python3
"""
BMad Service Validation Script
Validates that mem0 and Context7 MCP servers are accessible before BMad operations.
"""

import requests
import json
import sys
from typing import Dict, Tuple, Optional

class ServiceValidator:
    """Validates external services required by BMad agents."""
    
    def __init__(self):
        self.mem0_url = "http://localhost:8000"
        self.context7_url = "http://localhost:8765"
        
    def validate_mem0(self) -> Tuple[bool, str]:
        """Validate mem0 API accessibility."""
        try:
            # Check if mem0 API is accessible using docs endpoint
            response = requests.get(f"{self.mem0_url}/docs", timeout=5)
            if response.status_code == 200 and "Mem0 REST APIs" in response.text:
                return True, "✅ mem0 API accessible"
            else:
                return False, f"❌ mem0 API returned status {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"❌ mem0 API not accessible at {self.mem0_url}"
        except requests.exceptions.Timeout:
            return False, f"❌ mem0 API timeout at {self.mem0_url}"
        except Exception as e:
            return False, f"❌ mem0 API error: {str(e)}"
    
    def validate_context7(self) -> Tuple[bool, str]:
        """Validate Context7 MCP server accessibility."""
        try:
            # Check if Context7 MCP server is accessible using config endpoint
            response = requests.get(f"{self.context7_url}/api/v1/config/", timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "mem0" in data and "openmemory" in data:
                        return True, "✅ Context7 MCP server accessible"
                except:
                    pass
                return True, "✅ Context7 MCP server accessible"
            else:
                return False, f"❌ Context7 MCP server returned status {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"❌ Context7 MCP server not accessible at {self.context7_url}"
        except requests.exceptions.Timeout:
            return False, f"❌ Context7 MCP server timeout at {self.context7_url}"
        except Exception as e:
            return False, f"❌ Context7 MCP server error: {str(e)}"
    
    def validate_all_services(self) -> Dict[str, Dict[str, any]]:
        """Validate all required services."""
        results = {}
        
        # Validate mem0
        mem0_valid, mem0_msg = self.validate_mem0()
        results['mem0'] = {
            'valid': mem0_valid,
            'message': mem0_msg,
            'url': self.mem0_url
        }
        
        # Validate Context7
        context7_valid, context7_msg = self.validate_context7()
        results['context7'] = {
            'valid': context7_valid,
            'message': context7_msg,
            'url': self.context7_url
        }
        
        # Overall status
        results['overall'] = {
            'valid': mem0_valid and context7_valid,
            'message': "✅ All services accessible" if mem0_valid and context7_valid else "❌ Some services not accessible"
        }
        
        return results
    
    def print_validation_report(self, results: Dict[str, Dict[str, any]]) -> None:
        """Print a formatted validation report."""
        print("\n🔍 BMad Service Validation Report")
        print("=" * 40)
        
        # mem0 status
        print(f"📁 mem0 Memory System: {results['mem0']['message']}")
        print(f"   URL: {results['mem0']['url']}")
        
        # Context7 status
        print(f"📚 Context7 MCP Server: {results['context7']['message']}")
        print(f"   URL: {results['context7']['url']}")
        
        # Overall status
        print(f"\n🎯 Overall Status: {results['overall']['message']}")
        
        if not results['overall']['valid']:
            print("\n⚠️  BMad Agent Operations Should Not Proceed")
            print("   Please start required services before using BMad agents.")
            print("\n🚀 To start services:")
            print("   docker-compose up -d mem0 postgres-mem0 neo4j-mem0")
            print("   docker-compose up -d openmemory-mcp")
        else:
            print("\n✅ All systems ready for BMad operations!")

def main():
    """Main validation function."""
    validator = ServiceValidator()
    results = validator.validate_all_services()
    validator.print_validation_report(results)
    
    # Exit with appropriate code
    if results['overall']['valid']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 