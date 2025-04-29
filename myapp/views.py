from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse 
from django.views.decorators.csrf import csrf_exempt
from docx import Document as DocxDocument
import PyPDF2
from openai import OpenAI
from pgvector.django import CosineDistance
from .models import Document
from supabase import create_client
from io import BytesIO
url = "https://ucaugixwhmrxfaaoxqhd.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVjYXVnaXh3aG1yeGZhYW94cWhkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDY4NTgwMywiZXhwIjoyMDYwMjYxODAzfQ.gGTEc913BhGTMqPxpht4nCoCBGGu2uXdPmvSk_DwfR4"
supabase = create_client(url, key)
@csrf_exempt
@api_view(["POST"])
def get_file(request):
    try:
        files = request.FILES.getlist('files')  # same key 'files' from frontend

        

        for f in files: 

            if f.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                file_bytes = f.read()                       
                response = supabase.storage.from_("docs").upload(
                    path=f"uploads/{f.name}",
                    file=file_bytes,
                    file_options={"cache-control": "3600", "upsert": False, "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",}
                )
                print(response,'file uploaded to s3')
                file_stream = BytesIO(file_bytes)  # recreate a readable stream
                document = DocxDocument(file_stream)
                full_text = []

                for paragraph in document.paragraphs:
                    paragraph_text = paragraph.text.strip()
                    if paragraph_text:  # avoid empty lines
                        embeddings = process_embedding(paragraph_text)
                        response = create_object(embeddings, f.name, paragraph_text)

                    
                #send api request to supabase..
            if f.content_type == 'application/pdf':            
                file_bytes = f.read()                       
                response = supabase.storage.from_("docs").upload(
                    path=f"uploads/{f.name}",
                    file=file_bytes,
                    file_options={"cache-control": "3600", "upsert": False, "content-type": "application/pdf",}
                )
                print(response,'file uploaded to s3')
                f.seek(0)
                reader = PyPDF2.PdfReader(f)
                

                for page in reader.pages:
                    page_text = page.extract_text()
                    

                    if page_text:
                        page_text=' '.join(page_text.split())
                        print(page_text)

                        embeddings = process_embedding(page_text)
                        response = create_object(embeddings, f.name, page_text)    

        return JsonResponse({"message": "Files uploaded successfully"}, status=200)                
    
    except Exception as e:
        print('err')
        print(str(e))
        return JsonResponse({"message": str(e)}, status=400)   
        

            

@csrf_exempt
@api_view(["POST"])
def get_signed_url(request):
    try:
        filename = request.data.get('title')  # front sends the filename to download
        print("fsdafsadf FILENAME", filename)
        
        signed_url_response = supabase.storage.from_("docs").create_signed_url(
            path=f"uploads/{filename}",  # Adjust path according to your storage structure
            expires_in=3600  # 1 hour expiration
        )

        signed_url = signed_url_response['signedURL']

        return JsonResponse({"url": signed_url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def process_embedding(input_text):
    client = OpenAI(api_key="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")

    response = client.embeddings.create(
        input=input_text,
        model='text-embedding-3-small',
    )

    print(response.data[0].embedding)
    return response.data[0].embedding
    

    
def create_object(embedding, file_name, file_content):

    Document.objects.create(
        title=file_name,
        content=file_content,
        embedding=embedding,
    )




@csrf_exempt
def search_file(request):
    print('search_file_triggured')
    query_string = request.body
    print(f"query_string{query_string}")
    query_embedding = process_embedding(query_string)

    results = Document.objects.annotate(
        similarity=CosineDistance('embedding', query_embedding)
    ).order_by('similarity')[:30]

    result_array_title= []
    result_array_content = []
    print('search results')
    for result in results:
        print(result.title)
        if result.title in result_array_title:
            continue
        else:
            result_array_title.append(result.title)

    for title in result_array_title:
        documents_by_title_content = Document.objects.filter(title = str(title)).first().content
        result_array_content.append(documents_by_title_content)
    

    payload = {'title':result_array_title, 'content':result_array_content}

    print(payload)
        


        
    
    return JsonResponse({'data':payload},status=200)


# To privately access to specific files.
# We need:
# 1. boto3 => instantiate s3 client object in python (using aws access key and secrete key)
# 2. upload the django Document object to supabase and upload the fileobj to S3 with its s3 key (s3 key = to let s3 know what file I mean to download)
# 3. when user queries, retreive the Documnet object and its s3 key. create a private url using s3key that lasts for a certain time

# import boto3
# import uuid
# import os

# s3_client = boto3.client(
#     's3',
#     aws_access_key_id='...',
#     aws_secret_access_key='...',
#     region_name='us-west-1'
# )

# def upload_to_s3(file_obj, original_filename):
#     bucket_name = 'bucket name'

#     # Create a unique key (e.g., uploads/uuid.pdf)
#     file_ext = os.path.splitext(original_filename)[1]
#     s3_key = f"uploads/{uuid.uuid4()}{file_ext}"

#     s3_client.upload_fileobj(
#         file_obj, # request.FILES
#         bucket_name, 
#         s3_key,
#         ExtraArgs={"ContentType": file_obj.content_type}
#     )

#     return s3_key  # return the key so you can save it in your model
