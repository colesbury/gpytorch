import math
import torch
from torch import nn
from .kernel import Kernel


class SpectralMixtureKernel(Kernel):
    def __init__(self, n_mixtures, log_mixture_weight_bounds=(-100, 100),
                 log_mixture_mean_bounds=(-100, 100), log_mixture_scale_bounds=(-100, 100)):
        super(SpectralMixtureKernel, self).__init__()
        self.register_parameter('log_mixture_weights', nn.Parameter(torch.zeros(n_mixtures)),
                                bounds=log_mixture_weight_bounds)
        self.register_parameter('log_mixture_means', nn.Parameter(torch.zeros(n_mixtures)),
                                bounds=log_mixture_mean_bounds)
        self.register_parameter('log_mixture_scales', nn.Parameter(torch.zeros(n_mixtures)),
                                bounds=log_mixture_scale_bounds)

    def forward(self, x1, x2):
        batch_size, n, d = x1.size()
        _, m, _ = x2.size()

        if d > 1:
            raise RuntimeError(' '.join([
                'The spectral mixture kernel can only be applied'
                'to a single dimension at a time. To use on multi-dimensional data,',
                'use a product of SM kernels, one for each dimension.'
            ]))

        mixture_weights = self.log_mixture_weights.exp()
        mixture_means = self.log_mixture_means.exp()
        mixture_scales = self.log_mixture_scales.mul(2).exp_()

        sq_distance = torch.matmul(x1, x2.transpose(-1, -2)).mul_(2)

        x1_squared = torch.matmul(x1.unsqueeze(-2), x1.unsqueeze(-1))
        x1_squared = x1_squared.view(batch_size, n, 1).expand(batch_size, n, m)
        x2_squared = torch.matmul(x2.unsqueeze(-2), x2.unsqueeze(-1))
        x2_squared = x2_squared.view(batch_size, 1, m).expand(batch_size, n, m)

        sq_distance.add_(-x1_squared).add_(-x2_squared)  # sq_distance = -(x - z)^2

        distance = torch.sqrt(sq_distance.mul(-1))  # distance = (x-z)

        sq_distance.mul_(2 * math.pi ** 2)  # sq_distance = -2*pi^2*(x-z)^2

        res = None
        for weight, mean, scale in zip(mixture_weights, mixture_means, mixture_scales):
            weight = weight.expand(batch_size, n, m)
            mean = mean.expand(batch_size, n, m)
            scale = scale.expand(batch_size, n, m)

            sq_distance_factor = (scale * sq_distance).exp_()
            if res is None:
                res = weight * sq_distance_factor * torch.cos(2 * math.pi * mean * distance)
            else:
                res += weight * sq_distance_factor * torch.cos(2 * math.pi * mean * distance)
            # res += w_a^2*exp{-2\pi^2*\sigma_a^2*sq_distance}*cos(2\pi*\mu_a*distance)

        return res
