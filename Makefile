# Default environment variables
OS ?= alpine
OS_VERSION ?= 3.21
PKG ?= mpich
PKG_VERSION ?= 4.3.0
BUILD_ARGS ?= --no-cache

# Docker Hub repository settings
DOCKER_REPO ?= blik6126287
DOCKER_TAG ?= latest

# Base directory and image naming
BASE_DIR = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)
BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)
PUBLISH_IMAGE = $(DOCKER_REPO)/$(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)

# Find all Dockerfiles in the package directory
DOCKERFILES := $(wildcard $(BASE_DIR)/Dockerfile.*)

.PHONY: all build publish clean config

all: build

# Build all Dockerfile variants
build:
	@echo "Building all variants in $(BASE_DIR)"
	@if [ -z "$(DOCKERFILES)" ]; then \
		echo "No Dockerfiles found in $(BASE_DIR)"; \
		exit 1; \
	fi; \
	for dockerfile in $(DOCKERFILES); do \
		tag=$$(basename $$dockerfile | sed 's/Dockerfile\.//'); \
		echo "Building $(BASE_IMAGE):$$tag from $$dockerfile"; \
		docker build $(BUILD_ARGS) -f $$dockerfile -t $(BASE_IMAGE):$$tag $(BASE_DIR); \
	done

# Publish all built variants to Docker Hub
publish: build
	@echo "Publishing all variants to Docker Hub"
	@for dockerfile in $(DOCKERFILES); do \
		tag=$$(basename $$dockerfile | sed 's/Dockerfile\.//'); \
		echo "Publishing $(PUBLISH_IMAGE):$$tag"; \
		docker tag $(BASE_IMAGE):$$tag $(PUBLISH_IMAGE):$$tag; \
		docker push $(PUBLISH_IMAGE):$$tag; \
	done

# Clean up all built images
clean:
	@echo "Removing all variant images"
	@for dockerfile in $(DOCKERFILES); do \
		tag=$$(basename $$dockerfile | sed 's/Dockerfile\.//'); \
		echo "Removing $(BASE_IMAGE):$$tag"; \
		docker rmi $(BASE_IMAGE):$$tag 2>/dev/null || true; \
		echo "Removing $(PUBLISH_IMAGE):$$tag"; \
		docker rmi $(PUBLISH_IMAGE):$$tag 2>/dev/null || true; \
	done

# Display configuration details
config:
	@echo "Current configuration:"
	@echo "OS = $(OS)"
	@echo "OS_VERSION = $(OS_VERSION)"
	@echo "PKG = $(PKG)"
	@echo "PKG_VERSION = $(PKG_VERSION)"
	@echo "BUILD_ARGS = $(BUILD_ARGS)"
	@echo "BASE_DIR = $(BASE_DIR)"
	@echo "BASE_IMAGE = $(BASE_IMAGE)"
	@echo "PUBLISH_IMAGE = $(PUBLISH_IMAGE)"
	@echo "DOCKER_REPO = $(DOCKER_REPO)"
	@echo "DOCKER_TAG = $(DOCKER_TAG)"
	@echo "Found Dockerfiles:"
	@for dockerfile in $(DOCKERFILES); do \
		echo "  - $$dockerfile"; \
	done
