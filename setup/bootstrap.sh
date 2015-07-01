#!/usr/bin/env bash
set -x

apt-get install -y \
    git \
    htop \
    python3-setuptools \
    python3-scipy

easy_install3 gensim
easy_install3 stemming
easy_install3 progressbar2

cp /vagrant/setup/gitconfig /home/vagrant/.gitconfig
cp /vagrant/setup/vimrc /home/vagrant/.vimrc
cp /vagrant/setup/screenrc /home/vagrant/.screenrc

wget -q -O /vagrant/data/grc.lexicon.xml \
    http://tesserae.caset.buffalo.edu/data/common/grc.lexicon.xml
wget -q -O /vagrant/data/la.lexicon.xml \
    http://tesserae.caset.buffalo.edu/data/common/la.lexicon.xml
