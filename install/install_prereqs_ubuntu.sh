#!/bin/bash

#This script will install all the required prereqs for you, including compiling pyqt4.
# Please not that this will require approximately 201MB space minimum to do so.

mkdir build
cd build
sudo apt update
sudo apt install python2.7-dev -y build-essential

#Download SIP and PyQt4
wget https://sourceforge.net/projects/pyqt/files/sip/sip-4.19.2/sip-4.19.2.tar.gz
wget http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.12/PyQt4_gpl_x11-4.12.tar.gz

#Install SIP
tar xzf sip-4.19.2.tar.gz
cd sip-4.19.2/
python configure.py
make -B -j 8
sudo make install
cd ../

#Install all PyQt4 dependencies from aptitude
sudo apt install libxext-dev python-qt4 qt4-dev-tools build-essential libqtwebkit4 libqtwebkit-dev -y

#Install PyQt4
tar xzf PyQt4_gpl_x11-4.12.tar.gz
cd PyQt4_gpl_x11-4.12/
python configure-ng.py --confirm-license
make -B -j 8
sudo make install

#Remove the evidence :P
cd ../../
rm -rf build

sudo apt install python-pip -y
sudo pip install beautifulsoup4 requests pyglet six pyaml pyttsx
sudo apt remove python-sip
sudo apt install python-sip python-qt4

