#!/bin/bash

platforms=(epel-6-i386 fedora-16-i386)

python setup.py sdist
mv dist/python-pika-ssl-0.9.5.tar.gz ~/rpmbuild/SOURCES/
rpmbuild -ba pika.spec

for platform in "${platforms[@]}"
do
    /usr/bin/mock -r ${platform} --rebuild $HOME/rpmbuild/SRPMS/python-pika-ssl-0.9.5-2.*src.rpm
done
