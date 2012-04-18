%define short_name pika-ssl

Name:           python-%{short_name}
Version:        0.9.5
Release:        2%{?dist}
Summary:        AMQP 0-9-1 client library for Python

Group:          Development/Libraries
License:        MPLv1.1 or GPLv2
URL:            http://github.com/raphdg/pika

# The tarball comes from here:
# http://github.com/%{short_name}/%{short_name}/tarball/v%{version}
# GitHub has layers of redirection and renames that make this a troublesome
# URL to include directly.
Source0:        python-pika-ssl-0.9.5.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
Obsoletes:      python-pika

BuildRequires:  python-setuptools
BuildRequires:  python-devel
Requires:       python

%description
Pika is a pure-Python implementation of the AMQP 0-9-1 protocol that
tries to stay fairly independent of the underlying network support
library.


%prep
%setup -q -n python-pika-ssl-0.9.5


%build
%{__python} setup.py build


%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

# Remove egg info
%{__rm} -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
%dir %{python_sitelib}/pika
%{python_sitelib}/pika/*
%doc COPYING
%doc LICENSE-GPL-2.0
%doc LICENSE-MPL-Pika
%doc README.md
%doc THANKS
%doc examples
