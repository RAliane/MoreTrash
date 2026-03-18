FROM python:3.9-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install torch torchvision torchaudio
RUN pip install numpy scipy matplotlib tqdm

# Clone and set up Text2CAD
RUN git clone https://github.com/SadilKhan/Text2CAD.git
WORKDIR /workspace/Text2CAD
# Add any additional setup steps here, e.g.:
# RUN pip install -r requirements.txt

# Clone and set up DeepCAD
WORKDIR /workspace
RUN git clone https://github.com/rundiwu/DeepCAD.git
WORKDIR /workspace/DeepCAD
# Add any additional setup steps here, e.g.:
# RUN pip install -r requirements.txt

WORKDIR /workspace
