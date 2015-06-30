#!/usr/bin/env bash
set -x

apt-get update
apt-get install -y \
   git \
   screen \
   vim \
   htop \
   nginx \
   fcgiwrap \
   python-dev \
   python-numpy \
   python-scipy \
   python-pip

sudo pip install smart-open
sudo pip install stemming
sudo pip install gensim

cp /vagrant/setup/gitconfig /home/vagrant/.gitconfig
cp /vagrant/setup/vimrc /home/vagrant/.vimrc
cp /vagrant/setup/screenrc /home/vagrant/.screenrc
