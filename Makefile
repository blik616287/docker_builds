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

.PHONY: all build publish clean config debug list-files

all: build

# Debug command to find files
debug:
	@echo "Finding files in $(BASE_DIR):"
	@ls -la $(BASE_DIR)/
	@echo "Looking for Dockerfiles:"
	@find $(BASE_DIR) -type f -name "Dockerfile*" | sort
	@echo "Current directory: $$(pwd)"

# List detected Dockerfiles for building/publishing
list-files:
	@echo "Dockerfiles found in $(BASE_DIR):"
	@for f in $(BASE_DIR)/Dockerfile*; do \
		echo "  - $$f"; \
	done

# Build all Dockerfile variants
build:
	@echo "Building all variants in $(BASE_DIR)"
	@if [ ! -d "$(BASE_DIR)" ]; then \
		echo "Directory $(BASE_DIR) not found"; \
		exit 1; \
	fi; \
	FOUND=0; \
	for f in $(BASE_DIR)/Dockerfile*; do \
		if [ -f "$$f" ]; then \
			FOUND=1; \
			filename=$$(basename "$$f"); \
			if [ "$$filename" = "Dockerfile" ] || [ "$$filename" = "Dockerfile.base" ]; then \
				tag="base"; \
			else \
				tag=$$(echo "$$filename" | sed -e 's/^Dockerfile\.//' -e 's/^dockerfile\.//'); \
			fi; \
			echo "Building $(BASE_IMAGE):$$tag from $$f"; \
			docker build $(BUILD_ARGS) -f "$$f" -t $(BASE_IMAGE):$$tag $(BASE_DIR); \
		fi; \
	done; \
	if [ $$FOUND -eq 0 ]; then \
		echo "No Dockerfiles found in $(BASE_DIR)"; \
		exit 1; \
	fi

# Publish all built variants to Docker Hub
publish: build
	@echo "Publishing all variants to Docker Hub"
	@for f in $(BASE_DIR)/Dockerfile*; do \
		if [ -f "$$f" ]; then \
			filename=$$(basename "$$f"); \
			if [ "$$filename" = "Dockerfile" ] || [ "$$filename" = "Dockerfile.base" ]; then \
				tag="base"; \
			else \
				tag=$$(echo "$$filename" | sed -e 's/^Dockerfile\.//' -e 's/^dockerfile\.//'); \
			fi; \
			echo "Publishing $(PUBLISH_IMAGE):$$tag"; \
			docker tag $(BASE_IMAGE):$$tag $(PUBLISH_IMAGE):$$tag; \
			docker push $(PUBLISH_IMAGE):$$tag; \
		fi; \
	done

# Clean up all built images
clean:
	@echo "Removing all variant images"
	@for f in $(BASE_DIR)/Dockerfile*; do \
		if [ -f "$$f" ]; then \
			filename=$$(basename "$$f"); \
			if [ "$$filename" = "Dockerfile" ] || [ "$$filename" = "Dockerfile.base" ]; then \
				tag="base"; \
			else \
				tag=$$(echo "$$filename" | sed -e 's/^Dockerfile\.//' -e 's/^dockerfile\.//'); \
			fi; \
			echo "Removing $(BASE_IMAGE):$$tag"; \
			docker rmi $(BASE_IMAGE):$$tag 2>/dev/null || true; \
			echo "Removing $(PUBLISH_IMAGE):$$tag"; \
			docker rmi $(PUBLISH_IMAGE):$$tag 2>/dev/null || true; \
		fi; \
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
	@echo "Dockerfile search directory: $(BASE_DIR)"
	@echo "Found Dockerfiles:"
	@for f in $(BASE_DIR)/Dockerfile*; do \
		if [ -f "$$f" ]; then \
			echo "  - $$f"; \
		fi; \
	done
