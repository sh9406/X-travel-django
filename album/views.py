
# Create your views here.
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from .forms import UserForm, PhotoForm, TagForm
from .models import Photo, PhotoTag
import logging
import boto3
from botocore.exceptions import ClientError
from django.views.decorators.csrf import csrf_exempt

import io
# from PIL import Image
import cv2
import numpy as np
from base64 import b64decode

from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.http import JsonResponse

from album import forms


# presigned 아닌 사진 리스트
@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 조회
  user = get_user_model()
  photo_list=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
  id_list=list(photo_list.values_list('id',flat=True))
  photos=[]
  count = 0
  for a in photo_list:
    if a is not None:
    #   response = requests.get(url)
      photos.append({'url':a,'id':id_list[count]})
      count +=1
  context = {'photos':photos}
  return render(request, 'album.html', context)


def signup(request):

  if request.method == 'POST':
    form = UserForm(request.POST)

    if form.is_valid():
      form.save()
      username = form.cleaned_data.get('username')
      raw_password  = form.cleaned_data.get('password1')
      user = authenticate(username = username, password = raw_password)
      login(request, user)
      return redirect('/')

  else:
    form = UserForm()

  return render(request, 'signup.html', {'form' : form})

# 사진 업로드 함수
@login_required(login_url='login')
def upload(request): 
  """
  upload
  """
  if request.method== "POST":
    print('request method is post')
    print(request.POST)
    form = PhotoForm(request.POST)
    if form.is_valid():
      post = form.save(commit=False)  

      # photo가 입력되었는지 확인하고 넣어줌
      if 'photo' in request.FILES:
        photo=request.FILES['photo']
        photo_read=photo.read()
        photo.seek(0)
        
        # s3업로드
        photo_object_key='public/'+str(request.user.username)+'/'+str(photo)
        s3_upload_file(photo,'cloud01-2',photo_object_key)
        
        # s3링크저장
        # s3url = 's3://cloud01-2/'+photo_object_key
        s3url=create_url('cloud01-2',photo_object_key)
        post.photo=s3url

        # 태그 자동 삽입
        try:
          yolo(photo_read)
        except:
          print('yolo 태그 검출 실패')

      # author, create_date 지정
      post.author= request.user
      # post.create_date=timezone.now()

      # 세이브
      post.save()
      print('post save made')

      return redirect('index')

    else:
      print('form is not valid')

  else:
    print('request method is get -upload')
    form=PhotoForm()
    
  context = {'form': form }
  return render(request, 'upload.html', context )




#사진 삭제
@login_required(login_url='common:login')
def delete(request,post_id):
  if request.method== "GET":
    print('request method is get. - views.post_delete')
    post = get_object_or_404(Photo, pk=post_id)
    form = PhotoForm(request.POST)
    if form.is_valid():
      print('form is valid -delete')
      post.delete()
    else:
      print('post delete - form is not valid')

  return redirect('dailyphoto:profile', username = request.user.username)


def s3_upload_file(file_obj, bucket, object_name=None):
  """Upload a file to an S3 bucket

  :param file_name: File to upload
  :param bucket: Bucket to upload to
  :param object_name: S3 object name. If not specified then file_name is used
  :return: True if file was uploaded, else False
  """

  # If S3 object_name was not specified, use file_name
  basename=str(file_obj)

  if object_name is None:
      object_name = basename
  
  #확장자명 
  extension= str(basename).split('.')[-1]

  # Upload the file
  s3_client = boto3.client('s3')
  try:
      response = s3_client.upload_fileobj(file_obj, bucket, object_name,{'ContentType':extension})
      
  except ClientError as e:
      logging.error(e)
      return False
  return True


# url 생성 함수
def create_url(bucket_name,object_key):
  return f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_key}'


# 프리사인드 url 생성 함수 
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',Params={'Bucket': bucket_name,'Key': object_name},ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response

def s3_get(bucket,key):
  
  s3_client = boto3.client('s3')
  try:
    print(key)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    print(f'response = {response}')
    content=response['Body'].read()
    # print(f'content = {content}')
    return content
      
  except ClientError as e:
      logging.error(e)
      return False
  return True


def detail(request,photo_id):
  photo=Photo.objects.filter(id=photo_id)
  photo=photo.values('photo')
  # print(photo)
  photo=list(photo)[0]['photo']
  print(photo)

  if (photo[0]=='s') :
    url=photo.strip('s3://cloud01-2/')
    # print(url)
    url = create_presigned_url('cloud01-2', url)
    print(url)
  else:
    url=photo  

  tags=PhotoTag.objects.filter(photo_id=photo_id).values_list('tags',flat=True)

  # 태그가 존재하는가 
  if tags:
    tags=list(tags)
    print(f'tags{tags}')
  
  # 태그가 없을 경우 자동검출 
  else:
    # tags=리스트 스트링
    # tags= yolo(photo.read())
    key ='pu'+ url.strip('https://cloud01-2.s3.us-east-2.amazonaws.com') #앞에 두글자 짤리는 이유가 뭔지 모르겠다 
    pic= s3_get('cloud01-2',key)
    # print(pic)
    tags= yolo(pic)
    print(tags)

    # 태그 저장 
    for a_tag in tags:
      print(a_tag)
      # tagForm= TagForm()
      # print(tagForm)
      # # form.save( commit=False)
      # tagForm.tags=a_tag
      # tagForm.create_date=timezone.now()
      # print(tagForm.create_date)
      # tagForm.photo=Photo.objects.get(id=int(photo_id))
      # print(tagForm.photo)
      # # form.save()
      # print(tagForm)
      # for field in tagForm:
      #   print("Field Error:", field.name,  field.errors)

      tagForm= TagForm({'tags':a_tag,'photo':Photo.objects.get(id=int(photo_id)),'create_date':timezone.now()})
      print(tagForm)
      if tagForm.is_valid():
        tagForm.save()

      else:
        print('tagform is not valid')
        print(tagForm.errors)


  return render(request, 'detail.html', {'tags' : tags,'photo_id':photo_id,'photo':url})

def search_by_tag(request,tags):
  pass

def yolo(img_buffer):
  # Load Yolo
  net = cv2.dnn.readNet("album\yolov3-tiny-custom_final.weights", "album\yolov3-tiny-custom.cfg")
  classes = []
  with open("album\coco.names", "r") as f:
      classes = [line.strip() for line in f.readlines()]
  layer_names = net.getLayerNames()
  output_layers = [layer_names[i-1] for i in net.getUnconnectedOutLayers()]
  #output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
  colors = np.random.uniform(0, 255, size=(len(classes), 3))

  # Loading image
  img = cv2.imdecode(np.frombuffer(img_buffer, np.uint8), -1)
  img = cv2.resize(img, None, fx=0.4, fy=0.4)
  height, width, channels = img.shape

  # Detecting objects
  blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

  net.setInput(blob)
  outs = net.forward(output_layers)

  class_ids = []
  confidences = []
  boxes = []
  for out in outs:
    for detection in out:
        scores = detection[5:]
        class_id = np.argmax(scores)
        confidence = scores[class_id]
        if confidence > 0.5:
      # Object detected
            center_x = int(detection[0] * width)
            center_y = int(detection[1] * height)
            w = int(detection[2] * width)
            h = int(detection[3] * height)

      # Rectangle coordinates
            x = int(center_x - w / 2)
            y = int(center_y - h / 2)

            boxes.append([x, y, w, h])
            confidences.append(float(confidence))
            class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    print(indexes) 

    font = cv2.FONT_HERSHEY_PLAIN
    labels=[]
    for i in range(len(boxes)):
      if i in indexes:
        x, y, w, h = boxes[i]
        label = str(classes[class_ids[i]])
        labels.append(label)
        #color = colors[class_ids[i]]
        #cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        #cv2.putText(img, label, (x, y + 30), font, 3, color, 3)

    #cv2.imshow("Image", img)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    print('태그: '+label) #해시태그 작성

  return labels

@login_required(login_url='login')
def add_tag(request):
  print('add_tag 실행')
  print(request)
  print(request.POST)
  print(request.body)
  if request.method=="POST":
    form = TagForm(request.POST)
    if form.is_valid():
      tags=form.save(commit=False)
      print(request.POST['photo'])
      tags.photo=Photo.objects.get(id=int(request.POST['photo']))
      print(tags.photo)
      print(tags.photo.photo)
      print(request.POST['tags'])
      tags.tags=request.POST['tags']
      tags.create_date=timezone.now()
      # tags.imgurl=tags.photo.photo
      tags.save()
    else:
      print(form.errors.as_data()) 
      print('form is not valid')
  else:
    print('add_tag if문 빠져나옴 - request method is not post')

  return HttpResponse({'code': '200', 'msg': '태그 전송 성공'})


@login_required(login_url='login')
def detect_tag(request):
  print('사물 검출')
  print(request)
  print(request.POST)
  print(request.body)
  if request.method=="POST":
    form = TagForm(request.POST)
    if form.is_valid():
      # Load Yolo
        net = cv2.dnn.readNet("album\yolov3-tiny-custom_final.weights", "album\yolov3-tiny-custom.cfg")
        classes = []
        with open("album\coco.names", "r") as f:
            classes = [line.strip() for line in f.readlines()]
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i-1] for i in net.getUnconnectedOutLayers()]
        #output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
        colors = np.random.uniform(0, 255, size=(len(classes), 3))

      # Loading image
        img = cv2.imread('album\94.jpg')
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        height, width, channels = img.shape

      # Detecting objects
        blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

        net.setInput(blob)
        outs = net.forward(output_layers)

        class_ids = []
        confidences = []
        boxes = []
        for out in outs:
          for detection in out:
              scores = detection[5:]
              class_id = np.argmax(scores)
              confidence = scores[class_id]
              if confidence > 0.5:
            # Object detected
                  center_x = int(detection[0] * width)
                  center_y = int(detection[1] * height)
                  w = int(detection[2] * width)
                  h = int(detection[3] * height)

            # Rectangle coordinates
                  x = int(center_x - w / 2)
                  y = int(center_y - h / 2)

                  boxes.append([x, y, w, h])
                  confidences.append(float(confidence))
                  class_ids.append(class_id)

          indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
          print(indexes) 

          font = cv2.FONT_HERSHEY_PLAIN
          for i in range(len(boxes)):
            if i in indexes:
              x, y, w, h = boxes[i]
              label = str(classes[class_ids[i]])
              #color = colors[class_ids[i]]
              #cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
              #cv2.putText(img, label, (x + 15, y + 110), font, 3, color, 2)


            #cv2.imshow("Image", img)
            #cv2.waitKey(0)
            #cv2.destroyAllWindows()
          
          print('#'+label) #해시태그

    else:
      print(form.errors.as_data()) 
      print('form is not valid')
  else:
    print('사물 검출 if문 빠져나옴 - request method is not post')

  return HttpResponse()


#app_login api
class AppLoginView(APIView):
    def post(self, request):

        print(request.POST)
        id = request.POST.get('userid', '')
        pw = request.POST.get('userpw', '')

        user = authenticate(username=id, password=pw)
        token = Token.objects.get(user=user)

        if user:
            print("로그인 성공!")
            return JsonResponse({'token':token.key, 'code': '200', 'msg': '로그인 성공입니다.'}, status=200)
        else:
            print("실패")
            return JsonResponse({'token':'x','code': '404', 'msg': '로그인 실패입니다.'}, status=404)
            
#app_photo_uri_path save
class UploadView(APIView):
  def post(self,request,format=None):
    form = PhotoForm(request.POST)
    photo = request.POST.get('photo','')
    print(request.POST)

    if form.is_valid():
      post = form.save(commit=False)  

        # s3경로 
      s3url = 'https://cloud01-2.s3.us-east-2.amazonaws.com/public/' +str(request.user.username)+'/' + photo
      post.photo=s3url

      post.author = request.user

      # 세이브
      post.save()
      print('post save made')

      return JsonResponse({'code': '200', 'msg': '성공입니다.'}, status=200)
    else:
      return JsonResponse({'code': '404', 'msg': '실패입니다.'}, status=404)

class IndexView(APIView):
  def get(self,request,format=None):
    photos=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
    print(photos)    
    context = {'photos':photos}
    return render(request, 'album.html', context)

class ProfileView(APIView):
  def post(self,request,format=None):
        # 사진 개수
        count = Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True).count()
        print(count)
        if request.user:
          return JsonResponse({'count':count, 'code': '200', 'msg': '성공입니다.'}, status=200)
        else:
          return JsonResponse({'code': '404', 'msg': '실패입니다.'}, status=404)


