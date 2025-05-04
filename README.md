# reaktion-net

[![codecov](https://codecov.io/gh/arkitektio/omero-ark/branch/master/graph/badge.svg?token=UGXEA2THBV)](https://codecov.io/gh/arkitektio/arkitektio)
[![PyPI version](https://badge.fury.io/py/rekuest_next.svg)](https://pypi.org/project/rekuest/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://pypi.org/project/rekuest/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/rekuest_next.svg)](https://pypi.python.org/pypi/rekuest/)
[![PyPI status](https://img.shields.io/pypi/status/rekuest_next.svg)](https://pypi.python.org/pypi/rekuest/)

next gen fluss workflow scheduler plugin for rekuest

## Idea

reaktion is a scheduler extension for rekuest, it hooks into the agent and provides the "Deploy Flow" Node, that allows users to
choose the app as a scheduler for their workflows. When deploying a flow, this plugin will create a new workflow node, which can
now be reserved by any external app.

When reserving a workflow node, the plugin will create a new "Flow" Actor, which will be responsible for the execution of the
workflow. This actor will keep track of the state of the workflow and acts as the scheduler.

## Prerequesits

reaktion is a rekuest plugin and requires the rekuest library. While we are trying to reduce
the dependencies of rekuest, currently it makes only sense to use reaktion within the context of the arkitekt platform.
