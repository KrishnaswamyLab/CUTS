import torch
import torch.nn as nn
import torch.nn.functional as F
from data import PatchSampler


class CUTSEncoder(nn.Module):
    def __init__(self, in_channels: int = 3, num_kernels: int = 32, random_seed: int = None):
        super(CUTSEncoder, self).__init__()

        self.channels = in_channels

        self.batch_norm1 = nn.BatchNorm2d(num_kernels)
        self.batch_norm2 = nn.BatchNorm2d(num_kernels*2)
        self.batch_norm3 = nn.BatchNorm2d(num_kernels*4)

        self.conv1 = nn.Conv2d(in_channels, num_kernels,
                               kernel_size=3, padding='same')
        self.conv2 = nn.Conv2d(num_kernels, num_kernels*2,
                               kernel_size=3, padding='same')
        self.conv3 = nn.Conv2d(num_kernels*2, num_kernels*4,
                               kernel_size=3, padding='same')

        self.patch_sampler = PatchSampler(random_seed=random_seed)

        self.patch_size = 7  # Encoder includes 7 x 7 neighbor information

        # Reconstruction module.
        self.recon = CUTSRecon(channels=self.channels,
                               patch_size=self.patch_size)

    def forward(self, x):
        # `x` is the image input.
        B, C, _, _ = x.shape

        z = F.leaky_relu(self.batch_norm1(self.conv1(x)))
        z = F.leaky_relu(self.batch_norm2(self.conv2(z)))
        z = F.leaky_relu(self.batch_norm3(self.conv3(z)))

        # At this point, `z` is the latent projection of x.
        # We deliberately chose the layers such that the image-space resolution is the same.
        # In this way, we can (roughly) claim that z[i][j] is a feature representation
        # of the image patch centered at x[i][j].

        # Sample patches for contrastive loss & reconstruction loss
        # anchors_hw, positives_hw, negatives_hw = \
        anchors_hw, positives_hw = self.patch_sampler.sample(x)

        # These are containers that will later hold the torch.Tensors.
        # They won't track gradients themselves but the Tensors they contain will.
        x_anchors = torch.zeros(
            (B, C, self.patch_size, self.patch_size)).to(x.device)
        z_anchors = torch.zeros(
            (B, z.shape[1])).to(x.device)
        z_positives = torch.zeros_like(z_anchors).to(x.device)
        # z_negatives = torch.zeros_like(z_anchors).to(x.device)

        assert anchors_hw.shape[0] == B
        for batch_idx in range(B):
            for sample_idx in range(anchors_hw.shape[1]):
                x_anchors[batch_idx, ...] = x[batch_idx, :,
                                              anchors_hw[batch_idx, sample_idx, 0]-self.patch_size//2:
                                              anchors_hw[batch_idx, sample_idx, 0] -
                                              self.patch_size//2+self.patch_size,
                                              anchors_hw[batch_idx, sample_idx, 1]-self.patch_size//2:
                                              anchors_hw[batch_idx, sample_idx, 1]-self.patch_size//2+self.patch_size]
                z_anchors[batch_idx, ...] = z[batch_idx, :,
                                              anchors_hw[batch_idx,
                                                         sample_idx, 0],
                                              anchors_hw[batch_idx,
                                                         sample_idx, 1]
                                              ]
                z_positives[batch_idx, ...] = z[batch_idx, :,
                                                positives_hw[batch_idx,
                                                             sample_idx, 0],
                                                positives_hw[batch_idx,
                                                             sample_idx, 1]
                                                ]
                # z_negatives[batch_idx, ...] = z[batch_idx, :,
                #                                 negatives_hw[batch_idx,
                #                                              patch_idx, 0],
                #                                 negatives_hw[batch_idx,
                #                                              patch_idx, 1]
                #                                 ]

        # Reconstruction.
        # Reshape to [B, -1]
        x_anchors = x_anchors.reshape(x_anchors.shape[0], -1)
        x_recon = self.recon(z_anchors.reshape(z_anchors.shape[0], -1))

        return x_anchors, x_recon, z_anchors, z_positives  # , z_negatives


class CUTSRecon(nn.Module):
    """
    The low-budget reconstruction network, which is simply a linear layer.
    # TODO: Consider a convolutional reconstruction module.
    """

    def __init__(self, channels: int = None, patch_size: int = None):
        super(CUTSRecon, self).__init__()
        self.channels = channels
        self.patch_size = patch_size
        self.recon = nn.Linear(128, self.channels * self.patch_size**2)

    def forward(self, z):
        return self.recon(z)