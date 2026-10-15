SHELL := /bin/bash
.PHONY: help install setup status logs restart test check
help:
	@echo "VPS Control: make install | status | logs | restart | test"
install setup:
	sudo bash setup.sh
status:
	systemctl status vps-panel --no-pager
logs:
	sudo journalctl -u vps-panel -f
restart:
	sudo systemctl restart vps-panel
test check:
	python3 -m compileall -q control-panel podman-monitor traefik-routing network-gateway
	python3 -m unittest discover -s podman-monitor -p 'test_*.py' -v
	python3 -m unittest discover -s traefik-routing -p 'test_*.py' -v
	python3 -m unittest discover -s network-gateway -p 'test_*.py' -v
	python3 -m unittest discover -s control-panel -p 'test_observability.py' -v
