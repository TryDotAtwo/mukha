"""Small PyTorch oracle for the pinned Shiu/Brian2 linear LIF model.

Scheduling is part of the model. Stimulus is an explicit voltage increment in
the synapses phase, matching the external Poisson input's point of application.
This oracle is not a biologically validated MaleCNS model or flight controller.
"""
from dataclasses import dataclass
import math
import torch


@dataclass(frozen=True)
class Parameters:
    dt_ms: float = 0.1
    rest_mv: float = -52.0
    reset_mv: float = -52.0
    threshold_mv: float = -45.0
    membrane_ms: float = 20.0
    synapse_ms: float = 5.0
    refractory_ms: float = 2.2
    delay_ms: float = 1.8

    def ticks(self, milliseconds):
        n = round(milliseconds/self.dt_ms)
        if n < 0 or not math.isclose(n*self.dt_ms, milliseconds, abs_tol=1e-9):
            raise ValueError('interval must be a nonnegative integral number of ticks')
        return n

    def validate(self):
        if not all(math.isfinite(x) for x in vars(self).values()):
            raise ValueError('nonfinite parameter')
        if min(self.dt_ms,self.membrane_ms,self.synapse_ms) <= 0:
            raise ValueError('time constants must be positive')
        self.ticks(self.refractory_ms); self.ticks(self.delay_ms)


class LifReference:
    def __init__(self, n, pre, post, weights_mv, sensory=(), params=Parameters(), dtype=torch.float64):
        params.validate()
        self.p = params
        self.tick = 0
        self.v = torch.full((n,),params.rest_mv,dtype=dtype)
        self.g = torch.zeros(n,dtype=dtype)
        self.next_allowed = torch.zeros(n,dtype=torch.int64)
        self.refractory = torch.full((n,),params.ticks(params.refractory_ms),dtype=torch.int64)
        self.refractory[list(sensory)] = 0
        self.delay = params.ticks(params.delay_ms)
        self.ring = torch.zeros((self.delay+1,n),dtype=dtype)
        self.w = torch.sparse_coo_tensor(torch.tensor([post,pre],dtype=torch.int64),
            torch.tensor(weights_mv,dtype=dtype),(n,n)).coalesce()
        self.a = math.exp(-params.dt_ms/params.membrane_ms)
        self.b = math.exp(-params.dt_ms/params.synapse_ms)
        self.c = (params.dt_ms/params.membrane_ms*self.a if params.membrane_ms == params.synapse_ms
            else (self.a-self.b)*params.synapse_ms/(params.membrane_ms-params.synapse_ms))

    def step(self, voltage_jump):
        p = self.p
        allowed = self.tick >= self.next_allowed
        self.v = torch.where(allowed,p.rest_mv+self.a*(self.v-p.rest_mv)+self.c*self.g,self.v)
        self.g = torch.where(allowed,self.b*self.g,self.g)
        spikes = allowed & (self.v > p.threshold_mv)
        self.ring[self.tick % len(self.ring)] = spikes.to(self.v.dtype)
        arrivals = self.ring[(self.tick-self.delay) % len(self.ring)]
        incoming = torch.sparse.mm(self.w,arrivals[:,None]).flatten()
        self.g += torch.where(allowed,incoming,0)
        self.v += torch.where(allowed,torch.as_tensor(voltage_jump,dtype=self.v.dtype),0)
        self.v = torch.where(spikes,p.reset_mv,self.v)
        self.g = torch.where(spikes,0,self.g)
        self.next_allowed = torch.where(spikes,self.tick+self.refractory,self.next_allowed)
        self.tick += 1
        return spikes.clone()
