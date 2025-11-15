FROM ubuntu:22.04

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# ============================
# 1. 接收代理参数 (关键)
# ============================
# 即使我们用了国内源，GitHub 和 PPA 仍然需要代理
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY="localhost,127.0.0.1,mirrors.aliyun.com,pypi.tuna.tsinghua.edu.cn"

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

# ============================
# 2. 系统源加速 (阿里云)
# ============================
# 先把默认源换成阿里云，加速基础包下载
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# ============================
# 3. 安装 Python 3.11 和系统依赖
# ============================
# 注意：ppa:deadsnakes 位于国外，这步会自动使用我们传入的代理
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    build-essential git curl wget flex bison \
    libgmp-dev libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev \
    python3.11 python3.11-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 3.11 为默认版本
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3-config python3-config /usr/bin/python3.11-config 1

# ============================
# 4. 编译安装依赖库 (PBC & Charm)
# ============================
WORKDIR /build
# 这些步骤会走代理，因为 wget/git 地址在国外
RUN wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz && \
    tar -zxvf pbc-0.5.14.tar.gz && \
    cd pbc-0.5.14 && \
    ./configure && make && make install && \
    ldconfig

WORKDIR /charm-build
RUN git clone https://github.com/JHUISI/charm.git && \
    cd charm && \
    ./configure.sh && \
    python3 setup.py install

# 验证 charm-crypto 安装
RUN python3 -c "from charm.toolbox.pairinggroup import PairingGroup; group = PairingGroup('MNT224'); print('✅ Charm-crypto installed successfully')"

# 清理构建文件
RUN rm -rf /build /charm-build

# ============================
# 5. 安装 Python 依赖 (清华源加速)
# ============================
WORKDIR /app
COPY requirements.txt .

# 修正：添加 --ignore-installed 参数以解决 blinker 等系统包冲突
RUN python3 -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip3 install --no-cache-dir --ignore-installed -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# ============================
# 6. 复制代码与配置
# ============================
# 复制所有应用代码和模块 (保留你原来的复制逻辑)
COPY distributed/ ./distributed/
COPY distributed_tests/ ./distributed_tests/
COPY vc_smallness/ ./vc_smallness/
COPY vds_*.py ./
COPY test_*.py ./
COPY debug_*.py ./
COPY demo_*.py ./
COPY *.py ./

# 设置 Python 路径
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5001 5002 5003

# 默认命令
CMD ["/bin/bash"]