# reaktion-next

[![codecov](https://codecov.io/gh/arkitektio/omero-ark/branch/master/graph/badge.svg?token=UGXEA2THBV)](https://codecov.io/gh/arkitektio/arkitektio)
[![PyPI version](https://badge.fury.io/py/rekuest_next.svg)](https://pypi.org/project/rekuest/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://pypi.org/project/rekuest/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/rekuest_next.svg)](https://pypi.python.org/pypi/rekuest/)
[![PyPI status](https://img.shields.io/pypi/status/rekuest_next.svg)](https://pypi.python.org/pypi/rekuest/)

workflow scheduler  for arkitekt

## Idea

reaktion is a scheduler extension for rekuest, it hooks into the agent and provides the "Deploy Flow" Node, that allows users to
choose the app as a scheduler for their workflows. When deploying a flow, this plugin will create a new workflow node, which can
now be reserved by any external app.

When reserving a workflow node, the plugin will create a new "Flow" Actor, which will be responsible for the execution of the
workflow. This actor will keep track of the state of the workflow and acts as the scheduler.

## Prerequesits

Services: In order to use reaktion_next you need a working arkitekt server with both "rekuest" (remote app calling-service) and "fluss" -
(workflow design and run recording module)" installed.

Client: you need to install arkitekt-next with the "reaktion_next" extra enabled

### Use inside an Arktiekt "Plugin"App

Add the reaktion_next import to your imports

```python
from arkitekt_next import register
import reaktion_next # autoinstalls the scheduling extensions

@register
def do_something() -> None:
    """ Some other random installed functionaliry that is also provided """

```

Start your app via "arkitekt-next run dev". You should now see the
reaktion badge appear on the AgentPage and you will find the scheduler
in the Deploy Button subsection when deploying your app.

### Use inside an Arkitekt "Standalone App"

```python
from arkitekt import register, easy
import reaktion_next # autoinstalls the scheduling extensions

@register
def do_something() -> None:
    """ Some other random installed functionaliry that is also provided """



with easy("your_app_name", url="arkitekt-server-ulr") as e:
   e.run() # will start a normal arkitekt app with reaktion enabled

```

## Experimental: Local Scheduling

An Arkitekt app that imports reaktion_next can also run entire local workflows
the will call registered function in memory, and does not to copy data from and
to the arkitket server.
