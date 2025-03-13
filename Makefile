# Default environment variables
OS ?= alpine
OS_VERSION ?= 3.21
PKG ?= mpich
PKG_VERSION ?= 4.3.0
BUILD_ARGS ?= --no-cache

# Optional MPI dependencies for OpenFOAM
MPI_TYPE ?= mpich
MPI_VERSION ?= 4.3.0

# Dynamically set the Dockerfile directory based on OS
DOCKERFILE_DIR = $(PWD}/$(OS)

# Use consistent directory structure and image naming
BASE_DIR = $(OS)/$(OS_VERSION)
BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_base
TEST_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_test

# Special case for OpenFOAM with MPI dependency
ifeq ($(PKG), openfoam)
    BASE_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_base
    TEST_IMAGE = $(OS)$(OS_VERSION)_$(PKG)$(PKG_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_test
    MPI_BASE_IMAGE = $(OS)$(OS_VERSION)_$(MPI_TYPE)$(MPI_VERSION)_base
    
    # OpenFOAM Dockerfile paths - specify MPI implementation in filename
    BASE_DOCKERFILE = $(BASE_DIR)/$(PKG)/$(PKG_VERSION)/Dockerfile.$(MPI_TYPE).$(MPI_VERSION).base
    TEST_DOCKERFILE = $(BASE_DIR)/$(PKG)/$(PKG_VERSION)/Dockerfile.$(MPI_TYPE).$(MPI_VERSION).test
else
    # Standard Dockerfile paths for other packages
    BASE_DOCKERFILE = $(BASE_DIR)/$(PKG)/$(PKG_VERSION)/Dockerfile.base
    TEST_DOCKERFILE = $(BASE_DIR)/$(PKG)/$(PKG_VERSION)/Dockerfile.test
endif

# Get the directory containing the Dockerfile
BASE_DOCKERFILE_DIR = $(dir $(BASE_DOCKERFILE))
TEST_DOCKERFILE_DIR = $(dir $(TEST_DOCKERFILE))

# Check if custom Dockerfile exists in the inferred directory
CUSTOM_DOCKERFILE_EXISTS := $(shell test -f $(DOCKERFILE_DIR)/Dockerfile && echo 1 || echo 0)

# Check if dockerfiles exist in the specified directories
BASE_EXISTS := $(shell test -f $(BASE_DOCKERFILE) && echo 1 || echo 0)
TEST_EXISTS := $(shell test -f $(TEST_DOCKERFILE) && echo 1 || echo 0)

.PHONY: all build-base build-test run-test clean config build-custom

# Default target
all: 
	@echo "Using dockerfile directory: $(DOCKERFILE_DIR)"
	@if [ "$(CUSTOM_DOCKERFILE_EXISTS)" = "1" ]; then \
		$(MAKE) build-custom; \
	elif [ "$(PKG)" = "openfoam" ]; then \
		$(MAKE) build-openfoam; \
	elif [ "$(TEST_EXISTS)" = "1" ]; then \
		$(MAKE) build-base build-test run-test; \
	else \
		$(MAKE) build-base; \
	fi

# Target to build from a Dockerfile in the inferred directory
build-custom:
	@echo "Building from Dockerfile in directory: $(DOCKERFILE_DIR)"
	@echo "OS: $(OS), OS_VERSION: $(OS_VERSION), PKG: $(PKG), PKG_VERSION: $(PKG_VERSION)"
	@echo "Using image name: $(BASE_IMAGE)"
	@docker build $(BUILD_ARGS) -t $(BASE_IMAGE) $(DOCKERFILE_DIR)

# Special target for OpenFOAM builds
build-openfoam:
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

# Helper target to build the required MPI dependency for OpenFOAM
build-mpi-dep:
	@echo "Building required MPI dependency: $(MPI_BASE_IMAGE)"
	@$(MAKE) build-base OS=$(OS) OS_VERSION=$(OS_VERSION) PKG=$(MPI_TYPE) PKG_VERSION=$(MPI_VERSION)

build-base:
	@if [ "$(CUSTOM_DOCKERFILE_EXISTS)" = "1" ]; then \
		echo "Building custom image from Dockerfile in directory: $(DOCKERFILE_DIR)"; \
		$(MAKE) build-custom; \
	elif [ "$(BASE_EXISTS)" = "1" ]; then \
		echo "Building base image: $(BASE_IMAGE)"; \
		if [ "$(PKG)" = "openfoam" ]; then \
			if ! docker image inspect $(MPI_BASE_IMAGE) >/dev/null 2>&1; then \
				echo "MPI base image $(MPI_BASE_IMAGE) not found. Building it first..."; \
				$(MAKE) build-mpi-dep; \
			fi; \
		fi; \
		echo "Using build context: $(BASE_DOCKERFILE_DIR)"; \
		docker build $(BUILD_ARGS) -f $(BASE_DOCKERFILE) -t $(BASE_IMAGE) $(BASE_DOCKERFILE_DIR); \
	else \
		echo "Base Dockerfile not found at $(BASE_DOCKERFILE)."; \
		echo "Checking for Dockerfile in directory: $(DOCKERFILE_DIR)"; \
		if [ "$(CUSTOM_DOCKERFILE_EXISTS)" = "1" ]; then \
			echo "Found Dockerfile in directory: $(DOCKERFILE_DIR), building custom image."; \
			$(MAKE) build-custom; \
		else \
			echo "No Dockerfile found. Cannot proceed."; \
			exit 1; \
		fi; \
	fi

build-test: build-base
	@if [ "$(TEST_EXISTS)" = "1" ]; then \
		echo "Building test image: $(TEST_IMAGE)"; \
		echo "Using build context: $(TEST_DOCKERFILE_DIR)"; \
		docker build $(BUILD_ARGS) -f $(TEST_DOCKERFILE) -t $(TEST_IMAGE) $(TEST_DOCKERFILE_DIR); \
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
	-if [ "$(CUSTOM_DOCKERFILE_EXISTS)" = "1" ]; then docker rmi $(BASE_IMAGE); fi

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
	@echo "BASE_DIR = $(BASE_DIR)"
	@echo "BASE_IMAGE = $(BASE_IMAGE)"
	@echo "TEST_IMAGE = $(TEST_IMAGE)"
	@echo "BASE_DOCKERFILE = $(BASE_DOCKERFILE)"
	@echo "BASE_DOCKERFILE_DIR = $(BASE_DOCKERFILE_DIR)"
	@echo "TEST_DOCKERFILE = $(TEST_DOCKERFILE)"
	@echo "TEST_DOCKERFILE_DIR = $(TEST_DOCKERFILE_DIR)"
	@echo "DOCKERFILE_DIR = $(DOCKERFILE_DIR)"
	@echo "CUSTOM_DOCKERFILE_EXISTS = $(CUSTOM_DOCKERFILE_EXISTS)"
	@echo "BASE_DOCKERFILE exists: $(BASE_EXISTS)"
	@echo "TEST_DOCKERFILE exists: $(TEST_EXISTS)"

# Helper target to create directory structure for a new package
create-package-dirs:
	@echo "Creating directory structure for $(OS)/$(OS_VERSION)/$(PKG)/$(PKG_VERSION)"
	@mkdir -p $(BASE_DIR)/$(PKG)/$(PKG_VERSION)
	@echo "# Base image for $(PKG) $(PKG_VERSION) on $(OS) $(OS_VERSION)" > $(BASE_DOCKERFILE)
	@echo "FROM $(OS):$(OS_VERSION)" >> $(BASE_DOCKERFILE)
	@echo "# Add your instructions here" >> $(BASE_DOCKERFILE)
	@echo "Directory structure created at $(BASE_DIR)/$(PKG)/$(PKG_VERSION)"
	@echo "Base Dockerfile template created at $(BASE_DOCKERFILE)"

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
