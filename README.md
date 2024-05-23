# moondream modular vision service

This module implements the [rdk vision API](https://github.com/rdk/vision-api) in a viam-labs:vision:moondream model.

This model leverages the [Moondream tiny vision language model](https://github.com/vikhyat/moondream) to allow for image classification and querying.

The Moondream model and inference will run locally, and therefore speed of inference is highly dependant on hardware.

## Build and Run

To use this module, follow these instructions to [add a module from the Viam Registry](https://docs.viam.com/registry/configure/#add-a-modular-resource-from-the-viam-registry) and select the `viam-labs:vision:moondream` model from the [viam-labs moondream-vision module](https://app.viam.com/module/viam-labs/moondream-vision).

## Configure your vision service

> [!NOTE]  
> Before configuring your vision service, you must [create a machine](https://docs.viam.com/manage/fleet/machines/#add-a-new-machine).

Navigate to the **Config** tab of your robot’s page in [the Viam app](https://app.viam.com/).
Click on the **Service** subtab and click **Create service**.
Select the `vision` type, then select the `viam-labs:vision:moondream` model.
Enter a name for your vision service and click **Create**.

On the new service panel, copy and paste the following attribute template into your vision service's **Attributes** box:

```json
{
  "revision": "<optional model revision>"
}
```

> [!NOTE]  
> For more information, see [Configure a Robot](https://docs.viam.com/manage/configuration/).

### Attributes

The following attributes are available for `viam-labs:vision:yolov8` model:

| Name | Type | Inclusion | Description |
| ---- | ---- | --------- | ----------- |
| `revision` | string | **Required** |  Moondream model revision, defaults to "2024-03-06" |

### Example Configurations

```json
{
  "revision": "2024-03-06"
}
```

## API

The moondream resource provides the following methods from Viam's built-in [rdk:service:vision API](https://python.viam.dev/autoapi/viam/services/vision/client/index.html)

### get_classifications(image=*binary*, count)

### get_classifications_from_camera(camera_name=*string*, count)

Note: if using this method, any cameras you are using must be set in the `depends_on` array for the service configuration, for example:

```json
      "depends_on": [
        "cam"
      ]
```

By default, the Moondream model will be asked the question "describe this image".
If you want to ask a different question about the image, you can pass that question as the extra parameter "question".
For example:

``` python
moondream.get_classifications(image, 1, extra={"question": "what is the person wearing?"})
```
