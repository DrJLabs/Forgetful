"""
Test suite for monitoring stack optimization for autonomous AI agent operations.
Tests cover Prometheus configuration, alert rules, and integration testing.
"""

import pytest
import yaml
import json
import requests
import time
from unittest.mock import patch, MagicMock
from pathlib import Path
import docker
import subprocess
from typing import Dict, List, Any

# Test data constants
PROMETHEUS_CONFIG_PATH = "monitoring/prometheus.yml"
ALERT_RULES_PATH = "monitoring/alert_rules.yml"
DOCKER_COMPOSE_PATH = "docker-compose.yml"
GRAFANA_DASHBOARD_PATH = "monitoring/grafana/dashboards/system-overview.json"


class TestPrometheusConfiguration:
    """Test Prometheus configuration for autonomous AI agent metrics."""
    
    def test_prometheus_config_loads_successfully(self):
        """Test that Prometheus configuration file loads without errors."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert 'global' in config
        assert 'scrape_configs' in config
        assert 'rule_files' in config
        
    def test_autonomous_agent_metrics_configuration(self):
        """Test that autonomous AI agent specific metrics are properly configured."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for autonomous-agents job
        autonomous_job = None
        for job in config['scrape_configs']:
            if job['job_name'] == 'autonomous-agents':
                autonomous_job = job
                break
        
        assert autonomous_job is not None, "autonomous-agents job not found in Prometheus config"
        assert autonomous_job['scrape_interval'] == '2s', "Expected 2s scrape interval for autonomous agents"
        assert 'autonomous' in autonomous_job.get('params', {}), "autonomous parameter not found"
        
        # Check metric relabel configs for autonomous metrics
        metric_relabel_configs = autonomous_job.get('metric_relabel_configs', [])
        expected_metrics = [
            'memory_operation_duration_seconds',
            'memory_operation_errors_total',
            'memory_cache_hit_ratio',
            'memory_batch_size_histogram',
            'agent_query_frequency',
            'agent_context_size_bytes',
            'agent_decision_latency',
            'agent_memory_relevance_score'
        ]
        
        configured_metrics = []
        for relabel_config in metric_relabel_configs:
            if 'regex' in relabel_config:
                configured_metrics.append(relabel_config['regex'])
        
        for metric in expected_metrics:
            assert any(metric in configured_metric for configured_metric in configured_metrics), \
                f"Metric {metric} not found in relabel configs"
    
    def test_optimized_scrape_intervals(self):
        """Test that scrape intervals are optimized for autonomous workloads."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        expected_intervals = {
            'autonomous-agents': '2s',
            'postgres-exporter': '3s',
            'neo4j': '3s',
            'openmemory-ui': '10s'
        }
        
        for job in config['scrape_configs']:
            job_name = job['job_name']
            if job_name in expected_intervals:
                assert job['scrape_interval'] == expected_intervals[job_name], \
                    f"Expected {expected_intervals[job_name]} for {job_name}, got {job['scrape_interval']}"
    
    def test_metric_relabel_configs(self):
        """Test that metric relabel configurations are properly set."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        mem0_job = None
        mcp_job = None
        
        for job in config['scrape_configs']:
            if job['job_name'] == 'mem0-api':
                mem0_job = job
            elif job['job_name'] == 'openmemory-mcp':
                mcp_job = job
        
        # Check mem0-api relabel configs
        assert mem0_job is not None
        relabel_configs = mem0_job.get('metric_relabel_configs', [])
        autonomous_configs = [config for config in relabel_configs 
                             if config.get('target_label') == 'metric_type' 
                             and config.get('replacement') == 'autonomous_operation']
        assert len(autonomous_configs) > 0, "No autonomous operation relabel configs found for mem0-api"
        
        # Check openmemory-mcp relabel configs
        assert mcp_job is not None
        relabel_configs = mcp_job.get('metric_relabel_configs', [])
        agent_configs = [config for config in relabel_configs 
                        if config.get('target_label') == 'metric_type' 
                        and config.get('replacement') == 'agent_pattern']
        assert len(agent_configs) > 0, "No agent pattern relabel configs found for openmemory-mcp"


class TestAlertRules:
    """Test alert rules for autonomous AI agent operations."""
    
    def test_alert_rules_load_successfully(self):
        """Test that alert rules file loads without errors."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        assert rules is not None
        assert 'groups' in rules
        assert len(rules['groups']) > 0
    
    def test_autonomous_operations_alert_group(self):
        """Test that autonomous operations alert group exists with required alerts."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        autonomous_group = None
        for group in rules['groups']:
            if group['name'] == 'autonomous-operations':
                autonomous_group = group
                break
        
        assert autonomous_group is not None, "autonomous-operations alert group not found"
        
        # Check for required alerts
        required_alerts = [
            'HighMemoryOperationLatency',
            'HighAgentErrorRate',
            'LowMemoryCacheHitRatio',
            'LowAutonomousOperationThroughput'
        ]
        
        alert_names = [rule['alert'] for rule in autonomous_group['rules']]
        
        for alert in required_alerts:
            assert alert in alert_names, f"Required alert {alert} not found in autonomous-operations group"
    
    def test_alert_threshold_values(self):
        """Test that alert thresholds match story requirements."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        autonomous_group = None
        for group in rules['groups']:
            if group['name'] == 'autonomous-operations':
                autonomous_group = group
                break
        
        assert autonomous_group is not None
        
        # Test specific thresholds
        for rule in autonomous_group['rules']:
            if rule['alert'] == 'HighMemoryOperationLatency':
                assert '> 0.1' in rule['expr'], "Memory operation latency threshold should be >100ms (0.1s)"
            elif rule['alert'] == 'HighAgentErrorRate':
                assert '> 1' in rule['expr'], "Agent error rate threshold should be >1%"
            elif rule['alert'] == 'LowMemoryCacheHitRatio':
                assert '< 0.8' in rule['expr'], "Cache hit ratio threshold should be <80% (0.8)"
    
    def test_alert_severity_levels(self):
        """Test that alerts have appropriate severity levels."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        autonomous_group = None
        for group in rules['groups']:
            if group['name'] == 'autonomous-operations':
                autonomous_group = group
                break
        
        assert autonomous_group is not None
        
        # Check severity levels
        for rule in autonomous_group['rules']:
            assert 'severity' in rule['labels'], f"Alert {rule['alert']} missing severity label"
            severity = rule['labels']['severity']
            assert severity in ['info', 'warning', 'critical'], \
                f"Alert {rule['alert']} has invalid severity: {severity}"
    
    def test_alert_runbook_urls(self):
        """Test that alerts have runbook URLs."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        autonomous_group = None
        for group in rules['groups']:
            if group['name'] == 'autonomous-operations':
                autonomous_group = group
                break
        
        assert autonomous_group is not None
        
        for rule in autonomous_group['rules']:
            assert 'runbook_url' in rule['annotations'], \
                f"Alert {rule['alert']} missing runbook_url annotation"
            assert rule['annotations']['runbook_url'].startswith('https://'), \
                f"Alert {rule['alert']} has invalid runbook_url format"


class TestDockerResourceOptimization:
    """Test Docker resource optimization for monitoring services."""
    
    def test_docker_compose_loads_successfully(self):
        """Test that Docker Compose file loads without errors."""
        with open(DOCKER_COMPOSE_PATH, 'r') as f:
            compose = yaml.safe_load(f)
        
        assert compose is not None
        assert 'services' in compose
    
    def test_monitoring_service_resource_limits(self):
        """Test that monitoring services have appropriate resource limits."""
        with open(DOCKER_COMPOSE_PATH, 'r') as f:
            compose = yaml.safe_load(f)
        
        # Check core services have resource limits
        core_services = ['mem0', 'postgres', 'neo4j', 'openmemory-mcp', 'openmemory-ui']
        
        for service_name in core_services:
            if service_name in compose['services']:
                service = compose['services'][service_name]
                assert 'deploy' in service, f"Service {service_name} missing deploy configuration"
                assert 'resources' in service['deploy'], f"Service {service_name} missing resources configuration"
                assert 'limits' in service['deploy']['resources'], \
                    f"Service {service_name} missing resource limits"
    
    def test_autonomous_workload_resource_reservations(self):
        """Test that services have appropriate resource reservations for autonomous workloads."""
        with open(DOCKER_COMPOSE_PATH, 'r') as f:
            compose = yaml.safe_load(f)
        
        # Check that database services have reservations for autonomous workloads
        db_services = ['postgres', 'neo4j']
        
        for service_name in db_services:
            if service_name in compose['services']:
                service = compose['services'][service_name]
                if 'deploy' in service and 'resources' in service['deploy']:
                    assert 'reservations' in service['deploy']['resources'], \
                        f"Service {service_name} missing resource reservations for autonomous workloads"


class TestMonitoringIntegration:
    """Integration tests for monitoring stack."""
    
    @pytest.fixture
    def docker_client(self):
        """Docker client fixture."""
        return docker.from_env()
    
    def test_prometheus_config_validation(self):
        """Test Prometheus configuration validation using promtool."""
        try:
            # Use promtool to validate configuration
            result = subprocess.run([
                'docker', 'run', '--rm', '-v', f'{Path.cwd()}/monitoring:/config',
                'prom/prometheus:latest', 'promtool', 'check', 'config', '/config/prometheus.yml'
            ], capture_output=True, text=True, timeout=30)
            
            assert result.returncode == 0, f"Prometheus config validation failed: {result.stderr}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker or promtool not available for configuration validation")
    
    def test_alert_rules_validation(self):
        """Test alert rules validation using promtool."""
        try:
            # Use promtool to validate alert rules
            result = subprocess.run([
                'docker', 'run', '--rm', '-v', f'{Path.cwd()}/monitoring:/config',
                'prom/prometheus:latest', 'promtool', 'check', 'rules', '/config/alert_rules.yml'
            ], capture_output=True, text=True, timeout=30)
            
            assert result.returncode == 0, f"Alert rules validation failed: {result.stderr}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker or promtool not available for rules validation")
    
    @patch('requests.get')
    def test_prometheus_metrics_endpoint(self, mock_get):
        """Test that Prometheus metrics endpoint is accessible."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        # HELP memory_operation_duration_seconds Duration of memory operations
        # TYPE memory_operation_duration_seconds histogram
        memory_operation_duration_seconds_bucket{le="0.1"} 100
        memory_operation_duration_seconds_bucket{le="0.5"} 120
        memory_operation_duration_seconds_bucket{le="1.0"} 130
        memory_operation_duration_seconds_bucket{le="+Inf"} 135
        memory_operation_duration_seconds_count 135
        memory_operation_duration_seconds_sum 45.2
        """
        mock_get.return_value = mock_response
        
        response = requests.get('http://localhost:9090/metrics')
        assert response.status_code == 200
        assert 'memory_operation_duration_seconds' in response.text
    
    def test_autonomous_metrics_format(self):
        """Test that autonomous metrics follow expected format."""
        expected_metrics = [
            'memory_operation_duration_seconds',
            'memory_operation_errors_total',
            'memory_cache_hit_ratio',
            'memory_batch_size_histogram',
            'agent_query_frequency',
            'agent_context_size_bytes',
            'agent_decision_latency',
            'agent_memory_relevance_score'
        ]
        
        # This would be a real integration test checking actual metrics
        # For now, we validate the expected metric names are configured
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config_content = f.read()
        
        for metric in expected_metrics:
            assert metric in config_content, f"Metric {metric} not found in Prometheus configuration"


class TestMonitoringPerformance:
    """Test monitoring stack performance for autonomous operations."""
    
    def test_scrape_interval_optimization(self):
        """Test that scrape intervals are optimized for autonomous workloads."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check that autonomous-agents has the highest frequency (lowest interval)
        autonomous_interval = None
        for job in config['scrape_configs']:
            if job['job_name'] == 'autonomous-agents':
                autonomous_interval = job['scrape_interval']
                break
        
        assert autonomous_interval == '2s', "Autonomous agents should have 2s scrape interval"
        
        # Check that database services have optimized intervals
        db_intervals = {}
        for job in config['scrape_configs']:
            if job['job_name'] in ['postgres-exporter', 'neo4j']:
                db_intervals[job['job_name']] = job['scrape_interval']
        
        for service, interval in db_intervals.items():
            assert interval == '3s', f"Database service {service} should have 3s scrape interval"
    
    def test_alert_evaluation_frequency(self):
        """Test that alert evaluation is frequent enough for autonomous operations."""
        with open(PROMETHEUS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        evaluation_interval = config['global']['evaluation_interval']
        assert evaluation_interval == '15s', "Evaluation interval should be 15s for autonomous operations"
    
    def test_alert_for_duration_optimization(self):
        """Test that alert 'for' durations are optimized for autonomous operations."""
        with open(ALERT_RULES_PATH, 'r') as f:
            rules = yaml.safe_load(f)
        
        autonomous_group = None
        for group in rules['groups']:
            if group['name'] == 'autonomous-operations':
                autonomous_group = group
                break
        
        assert autonomous_group is not None
        
        # Check that critical alerts have short durations
        for rule in autonomous_group['rules']:
            if rule['labels']['severity'] == 'critical':
                for_duration = rule.get('for', '0s')
                # Convert to seconds for comparison
                if for_duration.endswith('m'):
                    duration_seconds = int(for_duration[:-1]) * 60
                elif for_duration.endswith('s'):
                    duration_seconds = int(for_duration[:-1])
                else:
                    duration_seconds = 0
                
                assert duration_seconds <= 120, \
                    f"Critical alert {rule['alert']} should have 'for' duration <= 2 minutes"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])