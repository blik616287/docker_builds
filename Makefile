# Default environment variables
OS ?= alpine
OS_VERSION ?= 3.21
PKG ?= mpich
PKG_VERSION ?= 4.3.0
BUILD_ARGS ?= --no-cache

# Image tags
BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_base
TEST_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_test

# Dockerfile paths
BASE_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.base
TEST_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.test

.PHONY: all build-base build-test run-test clean

all: build-base build-test run-test

build-base:
	@echo "Building base image: $(BASE_IMAGE)"
	docker build $(BUILD_ARGS) -f $(BASE_DOCKERFILE) -t $(BASE_IMAGE) .

build-test: build-base
	@echo "Building test image: $(TEST_IMAGE)"
	docker build $(BUILD_ARGS) -f $(TEST_DOCKERFILE) -t $(TEST_IMAGE) .

run-test: build-test
	@echo "Running test container"
	docker run $(TEST_IMAGE):latest

clean:
	@echo "Removing images"
	-docker rmi $(TEST_IMAGE)
	-docker rmi $(BASE_IMAGE)

config:
	@echo "Current configuration:"
	@echo "OS = $(OS)"
	@echo "OS_VERSION = $(OS_VERSION)"
	@echo "PKG = $(PKG)"
	@echo "PKG_VERSION = $(PKG_VERSION)"
	@echo "BUILD_ARGS = $(BUILD_ARGS)"
	@echo "BASE_IMAGE = $(BASE_IMAGE)"
	@echo "TEST_IMAGE = $(TEST_IMAGE)"
