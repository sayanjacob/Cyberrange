FROM kalilinux/kali-rolling
ENV DEBIAN_FRONTEND=noninteractive

# install ssh server and create a non-root user
RUN apt-get update && apt-get install -y openssh-server sudo \
 && useradd -m -s /bin/bash kaliuser \
 && echo 'kaliuser:KaliPass123!' | chpasswd \
 && mkdir -p /var/run/sshd

# Allow root login and ensure sshd runs in foreground
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config || true \
 && sed -i 's/PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config || true

EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]