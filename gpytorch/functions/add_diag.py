import torch
from torch.autograd import Function, Variable


class AddDiag(Function):
    def forward(self, input, diag):
        if diag.numel() != 1:
            raise RuntimeError('Input must be a single-element tensor')
        val = diag.squeeze()[0]

        diag_mat = Variable(torch.eye(input.size(-2), input.size(-1)).type_as(input))
        if input.ndimension() == 3:
            diag_mat = diag_mat.unsqueeze(0).expand_as(input)
        return diag_mat.mul_(val).add_(input)

    def backward(self, grad_output):
        input_grad = None
        diag_grad = None

        if self.needs_input_grad[0]:
            input_grad = grad_output

        if self.needs_input_grad[1]:
            diag_grad = grad_output.new().resize_(1).zero_()
            if grad_output.numel() == 1:
                diag_grad.fill_(grad_output.squeeze()[0])
            elif grad_output.ndimension() == 3:
                batch_indices = grad_output.new(grad_output.size(0), 1)
                torch.arange(0, grad_output.size(0), out=batch_indices[:, 0])
                diag_indices = grad_output.new(grad_output.size(1), 1)
                torch.arange(0, grad_output.size(1), out=diag_indices[:, 0])

                batch_indices = batch_indices.repeat(1, grad_output.size(1)).view(-1)
                diag_indices = diag_indices.repeat(grad_output.size(0), 1).view(-1)
                vals = grad_output[batch_indices, diag_indices, diag_indices]

                diag_grad.fill_(vals.sum())
            else:
                diag_grad.fill_(grad_output.trace())

        return input_grad, diag_grad
