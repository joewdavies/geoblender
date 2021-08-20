# Shaded relief maps in blender

## Tutorial

This guide will help you render 3D looking shaded-relief maps in Blender and prepare DEM data using QGIS in order to do so.
<br>
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/renders/world.jpg" width="50%"> <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/renders/greece.jpg" width="50%">

## Requirements
For this tutorial i used the following software:
    - Blender 2.92  
    - QGIS 3.20


I will be going through the whole process, using Wales as my area of interest.

## Table of Contents
1. [Prepare the DEM](#1)
2. [Prepare blender scene](#2)
3. [Plug the DEM into the plane](#3)
4. [Add modifier](#4)
5. [Add colour](#5)

### Step 1: Prepare the DEM <a name="1"></a>
- First download the elevation tiles from your preferred source. I usually get mine from [here](https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/elevation/copernicus-dem/elevation). In this example I am using a tile which covers wales.
<br>
- If you need to merge multiple tiles together for your area of interest then use raster > miscellaneous > merge
<br>
- If you wish to clip the DEM to a specific area then in QGIS use raster > extraction > clip raster by mask layer and use a polygon of your area of interest as 'mask layer'. In this example I used a polygon of Wales to clip the DEM, both of them being the same projection (EPSG:4326).
<br>
- Now reproject the DEM into your desired projection in QGIS using raster > projections > warp (reproject). In this example I am reprojecting to EPSG:27700 (British National Grid).
<br>
- Once you have your reprojected DEM, right click it in the layers tab and select export > saveas then in the popup window select 'rendered image' as the output mode. This rendered image is what we will use in Blender. <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/saveas.png">

 ## Step 2 : Prepare blender scene <a name="2"></a>
Please bear in mind that this will take longer the first time you do it, but once it is set up you can just reuse the project as a template and adjust the dimensions to the different DEMs.

#### Scene settings

- First delete the cube that is loaded by default (left click then delete key)
<br>
- Then we need to add a plane. This is done by selecting add > mesh > plane <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/addplane.png"> 
<br>
- Set the dimensions of the scene according to the dimensions of our DEM image (in this case, the rendered DEM is 2348 x 2604 so I will set the X in scene dimensions to 2348 and the Y to 2604) <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/scenedimensions.png"> Also notice that I set the % of the scene dimensions to 20%. This just means that renders will be a lot quicker whilst we are tinkering with different settings until we are happy. Once everything is ready we can crank it up to 100% (or for bigger DEMs whatever our computer is capable of!) and the render will take longer but will produce an image with a higher resolution.  
<br>
-we also need to make sure that the aspect ratio of our scene matches our DEM image. To do this, we can just set the scale of our plane to match the dimensions of our DEM. In this example my DEM is 2348 x 2604 so I will set the plane X scale to 2.348 and the Y scale to 2.604. <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/aspect.png">   
<br>
- Just like this % value of the scene dimensions, we can increase and decrease the 'render' value in the 'render properties' tab to determine how many passes blender takes for each pixel (higher = more detailed, lower = less detailed)  <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/rendervalue.png">   
<br>
- In the same tab, we must also set the render engine to 'cycles'. This enables blender to do its shaded-relief magic. If you have a powerful graphics card I reccommend chaning the 'device' to 'GPU compute' - that way renders will be much faster.
<br>

#### Lighting settings 

- We also need to configure the light source of our scene. We need to select sun as our light, so to do this left click the light object in the object collection (top right) then select the 'object data properties' panel then select sun, set the power to 6 and the angle to 90. Now open the object properties panel and put 0 for X, 45 for Y, and 135 for Z. 
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/light.png">   
<br>	
I wont go into detail as to why I've chosen these values, but for a more in-depth explanation on lighting shaded relief maps in blender [check out this tutorial](https://somethingaboutmaps.wordpress.com/blender-relief-tutorial-the-sun/). Feel free to play around with these values once we've done our first render.

#### Camera settings

Finally, we need to set our camera to how we want it. To do this, select the camera object in the object collection (top right) then set the following values:
<br>
- In the object properties panel, set the location X and Y values to 0, and the Z to 3
<br>
- Then set the rotation X Y and Z to 0

If the camera is too zoomed-in, adjust the focal length property (when using a perspective camera) or the orthographic scale (when using an orthographic camera). You can also adjust the Z position of the camera. For playing around with different camera angles I suggest switching to the '3D viewport' editor type and moving the camera by hand (see screenshot below). 
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/camera.png"> 

 ## Step 3 : Plug the DEM into the plane <a name="3"></a>
 - In order for the plane to use our DEM for elevation, we need to add a new material to our plane. To do this, select the plane in the object collections panel (top right), then change the editor mode to shader editor  <img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/editortype.png"> 
 <br>
 - Once in shader editor click 'new material' which should add two new nodes: a principled BSDF and a material output
 <br>
 - All we need to do is add an image texture by clicking add > image texture. When the node appears, click the open image button and select the DEM .tif file we prepared earlier.
 <br>
 - Now add a displacement node by selecting add > displacement.
 <br>
 - Click the 'color' circle of the image texture node and drag to the 'height' circle of the displacement node. Then do the same but from 'displacement' of the displacement node to 'displacement' of the material output. It should now look something like this:
 
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/shader1.png"> 

 ## Step 4 : Add modifier <a name="4"></a>

 If you render the image now (render > render image or F12) you should get something like this:
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/render1.png"> 

Which is not what we want (blender is not deforming the plane 'in 3D' it is just showing a 2D hillshade).

To change this lets add a modifier:

- click the blue spanner icon to open modifier properties then click add modifier > subdivision surface. Now select 'simple' as the type of subdivision algorithm then tick 'adaptive subdivision'.

Now press F12 to render again and you should ned up with something like this:
<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/render2.png"> 


 ## Step 5 : Add colour!  <a name="5"></a>

In order to add colour we can add a colour ramp which will use our DEM to determine the colour of each pixel.

- First add a colour ramp node with add > color ramp
<br>
- Plug the DEM image texture node 'color' into the 'fac' of the color ramp node and then the 'color' of the color ramp node into the 'color' of the principled BSDF shader node.
<br>
- Add color stops by using the '+' icon and click the color to open the color selector

<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/colorramp.png"> 


Play around with the colours and their positions on the ramp to make cool renders.

### Extra: Mask for AOI

If you are using a colour ramp with your DEM then you probably want to distinguish between features such as land and sea. This can be accomplished using a mask. Here I will briefly explain how I do this.

Step 1 : Rasterize vector polygon of AOI in QGIS (raster > conversion > rasterize) with the following options:
	
	value to burn: 1
	output units : pixels
	width resolution : width of final DEM tif in pixels
	height resolution : height of final DEM tif in pixels
	output extent: same extent as our final DEM tif
	no data value: -1
	output data type: byte


Step 2: Save the generated raster as a rendered image (export > saveas > outputmode = rendered image)

Step 3 : Open output raster in infranView (or your prefferred image editor), save as png > select black area as transparent color. (this is just how I do it, as long as you can use the alpha channel of the image to distinguish between your AOI and areas outside it then thats fine)

Step 4 : Use in blender to differentiate AOI from non-AOI areas. Here is an example of using a different colour input for land and sea:

<img src="https://raw.githubusercontent.com/JoeWDavies/geoblender/master/tutorial/screenshots/mask.png"> 




