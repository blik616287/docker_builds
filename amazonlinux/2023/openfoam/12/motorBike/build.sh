#!/bin/bash

# Loop through all Dockerfile.<suffix> files
for dockerfile in Dockerfile.*; do
    # Extract the tag from the filename (everything after Dockerfile.)
    tag=${dockerfile#Dockerfile.}
    echo "Building image with tag: $tag"
    # Build the Docker image
    docker build -t amazonlinux2023_openfoam12:$tag -f $dockerfile .
    if [ $? -eq 0 ]; then
        echo "Successfully built amazonlinux2023_openfoam12:$tag"
        # Tag the image for Docker Hub
        sudo docker tag amazonlinux2023_openfoam12:$tag blik6126287/amazonlinux2023_openfoam12:$tag
        # Push to Docker Hub
        sudo docker push blik6126287/amazonlinux2023_openfoam12:$tag
        echo "Successfully pushed blik6126287/amazonlinux2023_openfoam12:$tag"
    else
        echo "Failed to build amazonlinux2023_openfoam12:$tag"
    fi
    echo "----------------------------------------"
done

echo "All Dockerfiles processed."
