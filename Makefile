# Default environment variables
OS ?= alpine
OS_VERSION ?= 3.21
PKG ?= mpich
PKG_VERSION ?= 4.3.0
BUILD_ARGS ?= --no-cache

# Optional MPI dependencies for OpenFOAM
MPI_TYPE ?= mpich
MPI_VERSION ?= 4.3.0

# Image tags
BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_base
TEST_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_test

# Special case for OpenFOAM with MPI dependency
ifeq ($(PKG), openfoam)
    BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_base
    TEST_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_test
    MPI_BASE_IMAGE = $(OS)$(OS_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_base
    # OpenFOAM Dockerfile paths - specify MPI implementation in filename
    BASE_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.$(MPI_TYPE).$(MPI_VERSION).base
    TEST_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.$(MPI_TYPE).$(MPI_VERSION).test
else
    # Standard Dockerfile paths for other packages
    BASE_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.base
    TEST_DOCKERFILE = $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)/Dockerfile.test
endif

# Check if dockerfiles exist
BASE_EXISTS := $(shell test -f $(BASE_DOCKERFILE) && echo 1 || echo 0)
TEST_EXISTS := $(shell test -f $(TEST_DOCKERFILE) && echo 1 || echo 0)

.PHONY: all build-base build-test run-test clean config

# Conditionally include build-test and run-test in 'all' target based on TEST_DOCKERFILE existence
# Make sure that for OpenFOAM, we check for MPI dependencies before building
ifeq ($(PKG), openfoam)
all:
	@echo "Building OpenFOAM with $(MPI_TYPE) $(MPI_VERSION)"
	@echo "Checking for MPI base image $(MPI_BASE_IMAGE)..."
	@if docker image inspect $(MPI_BASE_IMAGE) >/dev/null 2>&1; then \
		echo "Found MPI base image $(MPI_BASE_IMAGE), proceeding with build."; \
	else \
		echo "MPI base image $(MPI_BASE_IMAGE) not found. Building it first..."; \
		$(MAKE) build-mpi-dep; \
	fi
	@$(MAKE) build-base
	@if [ "$(TEST_EXISTS)" = "1" ]; then \
		$(MAKE) build-test; \
		$(MAKE) run-test; \
	fi
else
	# Regular case for non-OpenFOAM builds
	@if [ "$(TEST_EXISTS)" = "1" ]; then \
		$(MAKE) build-base build-test run-test; \
	else \
		$(MAKE) build-base; \
	fi
endif

# Helper target to build the required MPI dependency for OpenFOAM
build-mpi-dep:
	@echo "Building required MPI dependency: $(MPI_BASE_IMAGE)"
	@$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=$(MPI_TYPE) PKG_VERSION=$(MPI_VERSION)

build-base:
	@if [ "$(BASE_EXISTS)" = "1" ]; then \
		echo "Building base image: $(BASE_IMAGE)"; \
		if [ "$(PKG)" = "openfoam" ]; then \
			# MPI check already done if coming from the 'all' target, but check again for direct calls to build-base \
			if ! docker image inspect $(MPI_BASE_IMAGE) >/dev/null 2>&1; then \
				echo "MPI base image $(MPI_BASE_IMAGE) not found. Building it first..."; \
				$(MAKE) build-mpi-dep; \
			fi; \
			docker build $(BUILD_ARGS) -f $(BASE_DOCKERFILE) -t $(BASE_IMAGE) .; \
		else \
			docker build $(BUILD_ARGS) -f $(BASE_DOCKERFILE) -t $(BASE_IMAGE) .; \
		fi; \
	else \
		echo "Base Dockerfile not found at $(BASE_DOCKERFILE). Cannot proceed."; \
		exit 1; \
	fi

build-test: build-base
	@if [ "$(TEST_EXISTS)" = "1" ]; then \
		echo "Building test image: $(TEST_IMAGE)"; \
		docker build $(BUILD_ARGS) -f $(TEST_DOCKERFILE) -t $(TEST_IMAGE) .; \
	else \
		echo "Test Dockerfile not found at $(TEST_DOCKERFILE). Skipping test build."; \
	fi

run-test: build-test
	@if [ "$(TEST_EXISTS)" = "1" ]; then \
		echo "Running test container"; \
		docker run $(TEST_IMAGE):latest; \
	else \
		echo "Test Dockerfile not found at $(TEST_DOCKERFILE). Skipping test run."; \
	fi

clean:
	@echo "Removing images"
	-if [ "$(TEST_EXISTS)" = "1" ]; then docker rmi $(TEST_IMAGE); fi
	-if [ "$(BASE_EXISTS)" = "1" ]; then docker rmi $(BASE_IMAGE); fi

config:
	@echo "Current configuration:"
	@echo "OS = $(OS)"
	@echo "OS_VERSION = $(OS_VERSION)"
	@echo "PKG = $(PKG)"
	@echo "PKG_VERSION = $(PKG_VERSION)"
	@if [ "$(PKG)" = "openfoam" ]; then \
		echo "MPI_TYPE = $(MPI_TYPE)"; \
		echo "MPI_VERSION = $(MPI_VERSION)"; \
		echo "MPI_BASE_IMAGE = $(MPI_BASE_IMAGE)"; \
	fi
	@echo "BUILD_ARGS = $(BUILD_ARGS)"
	@echo "BASE_IMAGE = $(BASE_IMAGE)"
	@echo "TEST_IMAGE = $(TEST_IMAGE)"
	@echo "BASE_DOCKERFILE = $(BASE_DOCKERFILE)"
	@echo "TEST_DOCKERFILE = $(TEST_DOCKERFILE)"
	@echo "BASE_DOCKERFILE exists: $(BASE_EXISTS)"
	@echo "TEST_DOCKERFILE exists: $(TEST_EXISTS)"

# Helper target to build all MPI and OpenFOAM variants
build-all-variants:
	@echo "Building MPICH variants..."
	$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=mpich PKG_VERSION=4.3.0
	@echo "Building OpenMPI variants..."
	$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=openmpi PKG_VERSION=5.0.7
	@echo "Building OpenFOAM variants with MPICH..."
	$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=openfoam PKG_VERSION=11 MPI_TYPE=mpich MPI_VERSION=4.3.0
	@echo "Building OpenFOAM variants with OpenMPI..."
	$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=openfoam PKG_VERSION=11 MPI_TYPE=openmpi MPI_VERSION=5.0.7
