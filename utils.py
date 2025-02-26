import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


class GS3D(object):
    '''
    Class for the GS algorithm.
    Inputs:
        batch_size   int, determines the batch size of the prediction
        num_iter   int, determines the number of iterations of the GS algorithm
        input_shape   tuple of shape (height, width)
    Returns:
        Instance of the object
    '''
    def __init__(self,
                 data_params,
                 model_params):
        self.shape = data_params['shape']
        self.plane_distance = model_params['plane_distance']
        self.wavelength = model_params['wavelength']
        self.ps = model_params['pixel_size']
        self.model = model_params
        self.zs = [-0.005*x for x in np.arange(1, (self.shape[-1]-1)//2+1)][::-1] + [0.005*x for x in np.arange(1, (self.shape[-1]-1)//2+1)]
        self.Hs = self.__get_H(self.zs, self.shape, self.wavelength, self.ps)

    def __get_H(self, zs, shape, lambda_, ps):
        Hs = []
        for z in zs:
            x, y = np.meshgrid(np.linspace(-shape[1]//2+1, shape[1]//2, shape[1]),
                               np.linspace(-shape[0]//2+1, shape[0]//2, shape[0]))
            fx = x/ps/shape[0]
            fy = y/ps/shape[1]
            exp = np.exp(-1j * np.pi * lambda_ * z * (fx**2 + fy**2))
            Hs.append(np.fft.fftshift(exp.astype(np.complex64)))
        Hs.insert(shape[-1] // 2, 0)
        return Hs

    def __propagate(self, cf, H):
        return np.fft.ifft2(np.fft.ifftshift(np.fft.fft2(np.fft.fftshift(cf))*H))

    def __forward(self, cf_slm, Hs, As):
        new_Z = []
        z0 = np.fft.ifftshift(np.fft.fft2(np.fft.fftshift(cf_slm)))
        for H, A in zip(Hs, As):
            if type(H)!=int:
                new_Z.append(A*np.exp(1j*np.angle(self.__propagate(z0, H))))
            else:
                new_Z.append(A*np.exp(1j*np.angle(z0)))
        return new_Z

    def __backward(self, Zs, Hs):
        slm_cfs = []
        for Z, H in zip(Zs, Hs[::-1]):
            if type(H)!=int:
                slm_cfs.append(np.fft.ifft2(np.fft.ifftshift(self.__propagate(Z, H))))
            else:
                slm_cfs.append(np.fft.ifft2(np.fft.ifftshift(Z)))
        cf_slm = np.exp(1j*np.angle(np.sum(np.array(slm_cfs), axis=0)))
        return cf_slm

    def get_phase(self, As, K):
        As = np.transpose(As, axes=(2, 0, 1))
        cf_slm = np.exp(1j * np.random.rand(*As.shape[1:]))
        while K:
            new_Zs = self.__forward(cf_slm, self.Hs, As)
            cf_slm = self.__backward(new_Zs, self.Hs)
            K -= 1
        return np.angle(cf_slm)




def gs2d(img, K):
    phi = np.random.rand(*list(img.shape)).astype(np.float32)
    while K:
        img_cf = img * np.exp(1.j * phi)
        slm_cf = np.fft.ifft2(np.fft.ifftshift(img_cf))
        slm_phi = np.angle(slm_cf)
        slm_cf = 1 * np.exp(1j * slm_phi)
        img_cf = np.fft.fftshift(np.fft.fft2(slm_cf))
        phi = np.angle(img_cf)
        k -= 1
    return slm_phi

def display_results(imgs, phases, recons, t):
    assert imgs.ndim == 4 and phases.ndim == 4 and recons.ndim == 4, "Dimensions don't match"
    for img, phase, recon in zip(imgs, phases, recons):
        if img.shape[-1] == 1:
            fig, axs = plt.subplots(1, 3, figsize=(9, 3), sharey=True, sharex=True)
            axs[0].imshow(np.squeeze(img), cmap='gray')
            axs[0].set_title('Target')
            axs[1].imshow(np.squeeze(phase), cmap='gray')
            axs[1].set_title('SLM Phase')
            axs[2].imshow(np.squeeze(recon), cmap='gray')
            axs[2].set_title('Simulation')
        else:
            fig, axs = plt.subplots(2, img.shape[-1] + 1, figsize = (3 * (img.shape[-1] + 1), 6), sharey = True, sharex = True)
            axs[0, -1].imshow(np.squeeze(phase))
            axs[0, -1].set_title('SLM Phase')
            for i in range(img.shape[-1]):
                axs[0, i].imshow(img[:, :, i], cmap='gray')
                axs[0, i].set_title('Target')
                axs[1, i].imshow(recon[:, :, i], cmap='gray')
                axs[0, i].set_title('Simulation')
        fig.suptitle('Inference time was {:.2f}ms'.format(t*1000), fontsize=16)

def get_propagate(data, model):
    shape = data['shape']
    zs = [-0.005*x for x in np.arange(1, (shape[-1]-1)//2+1)][::-1] + [0.005*x for x in np.arange(1, (shape[-1]-1)//2+1)]
    lambda_ = model['wavelength']
    ps = model['pixel_size']

    def __get_H(zs, shape, lambda_, ps):
        Hs = []
        for z in zs:
            x, y = np.meshgrid(np.linspace(-shape[1] // 2 + 1, shape[1] // 2, shape[1]),
                               np.linspace(-shape[0] // 2 + 1, shape[0] // 2, shape[0]))
            fx = x / ps / shape[0]
            fy = y / ps / shape[1]
            exp = np.exp(-1j * np.pi * lambda_ * z * (fx ** 2 + fy ** 2))
            Hs.append(exp.astype(np.complex64))
        return Hs

    def __prop__(cf_slm, H=None, center=False):
        if not center:
            H = tf.broadcast_to(tf.expand_dims(H, axis=0), tf.shape(cf_slm))
            cf_slm *= tf.signal.fftshift(H, axes=[1, 2])
        fft = tf.signal.ifftshift(tf.signal.fft2d(tf.signal.fftshift(cf_slm, axes=[1, 2])), axes=[1, 2])
        img = tf.cast(tf.expand_dims(tf.abs(tf.pow(fft, 2)), axis=-1), dtype=tf.dtypes.float32)
        return img

    def __phi_slm(phi_slm):
        i_phi_slm = tf.dtypes.complex(np.float32(0.), tf.squeeze(phi_slm, axis=-1))
        return tf.math.exp(i_phi_slm)

    Hs = __get_H(zs, shape, lambda_, ps)

    def propagate(phi_slm):
        frames = []
        cf_slm = __phi_slm(phi_slm)
        for H, z in zip(Hs, zs):
            frames.append(__prop__(cf_slm, tf.keras.backend.constant(H, dtype=tf.complex64)))

        frames.insert(shape[-1] // 2, __prop__(cf_slm, center=True))

        return tf.concat(values=frames, axis=-1)
    return propagate